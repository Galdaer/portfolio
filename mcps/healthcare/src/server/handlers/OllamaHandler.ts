/**
 * OllamaHandler - Integrates Ollama LLM with Healthcare MCP Server for administrative/documentation support.
 * Healthcare compliance disclaimer: This module provides AI-powered documentation and workflow support only.
 * No medical advice, diagnosis, or treatment recommendations are given.
 */

import fetch from 'node-fetch';

export class OllamaHandler {
    private readonly ollamaApiUrl: string;
    private readonly defaultModel: string;

    /**
     * @param ollamaApiUrl - The base URL for the Ollama API (e.g., http://host.docker.internal:11434)
     * @param defaultModel - The default Ollama model to use (e.g., "llama-3", "mistral", "phi-3")
     */
    constructor(ollamaApiUrl: string, defaultModel: string = "llama-3") {
        this.ollamaApiUrl = ollamaApiUrl.endsWith('/') ? ollamaApiUrl.slice(0, -1) : ollamaApiUrl;
        this.defaultModel = defaultModel;
    }

    /**
     * Generates documentation or workflow text using Ollama LLM.
     * @param prompt - The prompt or instruction for the LLM.
     * @param model - (Optional) The Ollama model to use.
     * @returns The generated text from Ollama.
     */
    async generateText(prompt: string, model?: string): Promise<string> {
        const url = `${this.ollamaApiUrl}/api/generate`;
        const payload = {
            prompt,
            model: model || this.defaultModel,
            stream: false
        };

        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Ollama API error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        // Ollama returns { response: "...", ... }
        return data.response || "";
    }
}
