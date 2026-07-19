import os
from dotenv import load_dotenv

load_dotenv()

class LLMWrapper:
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generates text from the LLM given a prompt."""
        raise NotImplementedError

class GeminiWrapper(LLMWrapper):
    def __init__(self, model_name="gemini-1.5-flash"):
        # pyrefly: ignore [missing-import]
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY not found in environment.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
    def generate_text(self, prompt: str, **kwargs) -> str:
        response = self.model.generate_content(prompt)
        return response.text

class OpenAICompatibleWrapper(LLMWrapper):
    def __init__(self, base_url, api_key, model_name):
        # pyrefly: ignore [missing-import]
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model_name = model_name
        
    def generate_text(self, prompt: str, **kwargs) -> str:
        messages = []
        if "system_prompt" in kwargs:
            messages.append({"role": "system", "content": kwargs.pop("system_prompt")})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content

def get_llm(provider="gemini", model_name=None) -> LLMWrapper:
    """
    Factory function to get an LLM client wrapper.
    Supported providers: 'gemini', 'groq', 'openrouter', 'ollama'
    """
    provider = provider.lower()
    
    if provider == "gemini":
        return GeminiWrapper(model_name=model_name or "gemini-1.5-flash")
        
    elif provider == "groq":
        # Groq provides OpenAI compatibility
        return OpenAICompatibleWrapper(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY", "dummy_key"),
            model_name=model_name or "llama-3.1-8b-instant"
        )
        
    elif provider == "openrouter":
        # OpenRouter provides OpenAI compatibility
        return OpenAICompatibleWrapper(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY", "dummy_key"),
            model_name=model_name or "meta-llama/llama-3-8b-instruct:free"
        )
        
    elif provider == "ollama":
        # Ollama local endpoint usually runs on port 11434 with OpenAI compatibility
        return OpenAICompatibleWrapper(
            base_url="http://localhost:11434/v1",
            api_key="ollama", # OpenAI client requires some string here
            model_name=model_name or "llama3"
        )
        
    else:
        raise ValueError(f"Unknown provider: {provider}. Supported: gemini, groq, openrouter, ollama")

if __name__ == "__main__":
    # Simple test script (requires the respective backend running or API key set)
    print("Testing LLM Wrapper Factory...")
    print("Available providers: gemini, groq, openrouter, ollama")
    
    # Example usage:
    # llm = get_llm("ollama")
    # print(llm.generate_text("Hello, what is 2+2?"))
