import { AuthorizationCode } from 'simple-oauth2';
import express from 'express';
import { randomUUID } from 'node:crypto';
import { platform } from 'node:os';
import { exec } from 'node:child_process';
import { AuthConfig, Token } from "./AuthConfig.js";
import { fileURLToPath } from 'url';
import axios from 'axios';

interface StateHandler {
    resolve: (value: any) => void;
    reject: (error: Error) => void;
    pendingOperation: () => Promise<any>;
}

export class Auth {
  private authConfig:any;
  private oauth2: AuthorizationCode;
  private authState = new Map<string, StateHandler>();
  private token: Token | null = null;
  private callbackServer: any;

  constructor(authConfig:AuthConfig) {
    this.authConfig = authConfig;
      
    this.oauth2 = new AuthorizationCode({
      client: {
        id: authConfig.clientId,
        secret: authConfig.clientSecret
      },
      auth: {
        tokenHost: authConfig.tokenHost,
        tokenPath: authConfig.tokenPath,
        authorizePath: authConfig.authorizePath
      }
    });

    this.oauth2.authorizeURL({
      redirect_uri: this.authConfig.callbackURL,
      scope: this.authConfig.scopes,
      state: randomUUID()
    });
    
    this.setupCallbackServer();
  }

  public openBrowser = async (url: string) => {
    // Platform-specific commands
    const commands:any = {
      darwin: `open "${url}"`,              // macOS
      win32: `start "" "${url}"`,           // Windows 
      linux: `xdg-open "${url}"`            // Linux
    };
    
    const cmd = commands[platform()];
    if (!cmd) {
      throw new Error('Unsupported platform');
    }
  
    return new Promise((resolve, reject) => {
      exec(cmd, (error:any) => {
        if (error) reject(error);
        else resolve(undefined);
      });
    });
  };

  private async refreshToken(): Promise<void> {
    if (!this.token?.refresh_token) {
      throw new Error('No refresh token available');
    }

    try {
      const result = await this.oauth2.createToken({
        refresh_token: this.token.refresh_token
      }).refresh();

      this.token = {
        access_token: result.token.access_token as string   ,
        refresh_token: result.token.refresh_token as string,
        expires_at: new Date(result.token.expires_at as string)
      };
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.token = null;
      throw error;
    }
  }

  private isTokenExpired(): boolean {
    if (!this.token?.expires_at) return true;
    // Add 5 minute buffer
    return new Date(this.token.expires_at).getTime() - 5 * 60 * 1000 < Date.now();
  }

  async ensureValidToken(): Promise<string> {
    if (!this.token) {
      throw new Error('No token available');
    }

    if (this.isTokenExpired()) {
      await this.refreshToken();
    }

    return this.token.access_token;
  }
    
  private async exchangeCodeForToken(code: string, authMethod: 'body' | 'header' = 'body'): Promise<Token> {
    // Always include these in body
    const params = new URLSearchParams();
    params.append('grant_type', 'authorization_code');
    params.append('code', code);
    params.append('redirect_uri', this.authConfig.callbackURL);

    // Add credentials based on auth method
    if (authMethod === 'body') {
      params.append('client_id', this.authConfig.clientId);
      params.append('client_secret', this.authConfig.clientSecret);
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/x-www-form-urlencoded'
    };

    // Add Basic auth header if using header method
    if (authMethod === 'header') {
      const credentials = Buffer.from(`${this.authConfig.clientId}:${this.authConfig.clientSecret}`).toString('base64');
      headers['Authorization'] = `Basic ${credentials}`;
    }

    let tokenUrl = `${this.authConfig.tokenHost}${this.authConfig.tokenPath}`
    let response:any = null
    try {
        response = await axios.post(
            tokenUrl,
            params.toString(), // Send params as urlencoded string in body
            { headers }
        );
    } catch (error) {
        throw new Error(`Error getting token: ${error} . URL: ${tokenUrl}`);
    }

    return {
      access_token: response.data.access_token,
      refresh_token: response.data.refresh_token,
      expires_at: new Date(Date.now() + response.data.expires_in * 1000)
    };
  }

  private setupCallbackServer() {
    const app = express();
    const port = this.authConfig.callbackPort;
    
    //callback handler
    app.get('/oauth/callback', async (req, res) => {      
        const { code, state, error } = req.query;
        const stateHandler = this.authState.get(state as string);
  
        if (!stateHandler) {
          console.error('No state handler found for state:', state);
          res.status(400).send('Invalid state');
          return;
        }

        try {
            if (error) {
              stateHandler.reject(new Error(error as string));
            } else {
              const token:Token = await this.exchangeCodeForToken(code as string,this.authConfig.authorizationMethod);
              this.token = token;
              // Execute the pending operation with the new token
              const result = await stateHandler.pendingOperation();
              stateHandler.resolve(result);
            }
          } catch (err) {
            stateHandler.reject(err as Error);
          } finally {
            this.authState.delete(state as string);
        }
        try {
            const filePath = fileURLToPath(new URL('./auth-success.html', import.meta.url));
            res.sendFile(filePath);
        } catch (error) {
            console.error('Error reading auth success template:', error);
            res.send('Authentication successful! You can close this window.');
        }
    });
    
    // Add a test endpoint to verify server is running
    app.get('/health', (req, res) => {
      res.send('OAuth callback server is running');
    });

    this.callbackServer = app.listen(port, () => {
        // console.log(`OAuth callback server listening at http://localhost:${port}`);
    });

    this.callbackServer.on('error', (error:any) => {
      if ((error as any).code === 'EADDRINUSE') {
        throw new Error(`Port ${port} is already in use`);
      }
    });

    // Add graceful shutdown
    process.on('SIGTERM', () => {
      this.callbackServer.close(() => {
        console.log('OAuth server closed');
      });
    });
  }

  async executeWithAuth<T>(operation: () => Promise<T>): Promise<T> {
    try {
      if (this.token) {
        await this.ensureValidToken();
        return await operation();
      }

      // Need to authenticate first
      return new Promise((resolve, reject) => {
        const state = randomUUID();
        this.authState.set(state, {
          resolve,
          reject,
          pendingOperation: operation
        });

        const baseAuthUrl = this.oauth2.authorizeURL({
          redirect_uri: this.authConfig.callbackURL,
          scope: this.authConfig.scopes,
          state: state
        });

        // Add audience parameter manually
        const authUrl = new URL(baseAuthUrl);
        authUrl.searchParams.append('aud', this.authConfig.audience);
        const authorizationUri = authUrl.toString();

        this.openBrowser(authorizationUri).catch(reject);

      });
    } catch (error:any) {
      if (error.message.includes('refresh')) {
        this.token = null;
        return this.executeWithAuth(operation);
      }
      throw error;
    }
  }

  cleanup() {
    if (this.callbackServer) {
      this.callbackServer.close();
    }
  }
}

export default Auth;
