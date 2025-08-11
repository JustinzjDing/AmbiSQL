from openai import OpenAI
import asyncio

class LLMCaller:
    def __init__(self, model, max_concurrency=1):
        self.model = model
        self.total_tokens_used = 0  
        self.input_tokens = 0 
        self.output_tokens = 0
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError as e:
            if "There is no current event loop" in str(e):
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
            else:
                raise
        self.semaphore = asyncio.Semaphore(max_concurrency, loop=self.loop)
        
        api_key = 'YOUR_OPENAI_API_KEY'
        
        if model == 'gpt':
            self.model = "gpt-4o-2024-08-06"
        elif model == 'claude':
            self.model = "claude-opus-4-20250514"
        else:
            raise ValueError(f"Model {model} not recognized. Available models: 'gpt' and 'claude'.")
        
        self.client = OpenAI(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key = api_key
        )
    
    def call(self, query):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=query
        )
        if response.usage:
            self.total_tokens_used += response.usage.total_tokens
            self.input_tokens += response.usage.prompt_tokens
            self.output_tokens += response.usage.completion_tokens
        return response.choices[0].message.content

    async def async_call(self, query):
        
        async with self.semaphore:
            response = await asyncio.to_thread(lambda: self.client.chat.completions.create(model=self.model, messages=query))
            if response.usage:
                self.total_tokens_used += response.usage.total_tokens
                self.input_tokens += response.usage.prompt_tokens
                self.output_tokens += response.usage.completion_tokens
            return response.choices[0].message.content

    async def call_batch_async(self, queries):
        async def delayed_call(query):
            await asyncio.sleep(0.1)
            return await self.async_call(query)
        tasks = [delayed_call(query) for query in queries]
        results = await asyncio.gather(*tasks)
        return results


    def get_total_tokens_used(self):
        return self.total_tokens_used, self.input_tokens, self.output_tokens