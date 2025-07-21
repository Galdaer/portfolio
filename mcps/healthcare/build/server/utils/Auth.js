import { AuthorizationCode } from 'simple-oauth2';
import express from 'express';
import { randomUUID } from 'node:crypto';
import { platform } from 'node:os';
import { exec } from 'node:child_process';
import { fileURLToPath } from 'url';
import axios from 'axios';
export class Auth {
    authConfig;
    oauth2;
    authState = new Map();
    token = null;
    callbackServer;
    constructor(authConfig) {
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
    openBrowser = async (url) => {
        // Platform-specific commands
        const commands = {
            darwin: `open "${url}"`, // macOS
            win32: `start "" "${url}"`, // Windows 
            linux: `xdg-open "${url}"` // Linux
        };
        const cmd = commands[platform()];
        if (!cmd) {
            throw new Error('Unsupported platform');
        }
        return new Promise((resolve, reject) => {
            exec(cmd, (error) => {
                if (error)
                    reject(error);
                else
                    resolve(undefined);
            });
        });
    };
    async refreshToken() {
        if (!this.token?.refresh_token) {
            throw new Error('No refresh token available');
        }
        try {
            const result = await this.oauth2.createToken({
                refresh_token: this.token.refresh_token
            }).refresh();
            this.token = {
                access_token: result.token.access_token,
                refresh_token: result.token.refresh_token,
                expires_at: new Date(result.token.expires_at)
            };
        }
        catch (error) {
            console.error('Token refresh failed:', error);
            this.token = null;
            throw error;
        }
    }
    isTokenExpired() {
        if (!this.token?.expires_at)
            return true;
        // Add 5 minute buffer
        return new Date(this.token.expires_at).getTime() - 5 * 60 * 1000 < Date.now();
    }
    async ensureValidToken() {
        if (!this.token) {
            throw new Error('No token available');
        }
        if (this.isTokenExpired()) {
            await this.refreshToken();
        }
        return this.token.access_token;
    }
    async exchangeCodeForToken(code, authMethod = 'body') {
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
        const headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        };
        // Add Basic auth header if using header method
        if (authMethod === 'header') {
            const credentials = Buffer.from(`${this.authConfig.clientId}:${this.authConfig.clientSecret}`).toString('base64');
            headers['Authorization'] = `Basic ${credentials}`;
        }
        let tokenUrl = `${this.authConfig.tokenHost}${this.authConfig.tokenPath}`;
        let response = null;
        try {
            response = await axios.post(tokenUrl, params.toString(), // Send params as urlencoded string in body
            { headers });
        }
        catch (error) {
            throw new Error(`Error getting token: ${error} . URL: ${tokenUrl}`);
        }
        return {
            access_token: response.data.access_token,
            refresh_token: response.data.refresh_token,
            expires_at: new Date(Date.now() + response.data.expires_in * 1000)
        };
    }
    setupCallbackServer() {
        const app = express();
        const port = this.authConfig.callbackPort;
        //callback handler
        app.get('/oauth/callback', async (req, res) => {
            const { code, state, error } = req.query;
            const stateHandler = this.authState.get(state);
            if (!stateHandler) {
                console.error('No state handler found for state:', state);
                res.status(400).send('Invalid state');
                return;
            }
            try {
                if (error) {
                    stateHandler.reject(new Error(error));
                }
                else {
                    const token = await this.exchangeCodeForToken(code, this.authConfig.authorizationMethod);
                    this.token = token;
                    // Execute the pending operation with the new token
                    const result = await stateHandler.pendingOperation();
                    stateHandler.resolve(result);
                }
            }
            catch (err) {
                stateHandler.reject(err);
            }
            finally {
                this.authState.delete(state);
            }
            try {
                const filePath = fileURLToPath(new URL('./auth-success.html', import.meta.url));
                res.sendFile(filePath);
            }
            catch (error) {
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
        this.callbackServer.on('error', (error) => {
            if (error.code === 'EADDRINUSE') {
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
    async executeWithAuth(operation) {
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
        }
        catch (error) {
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
