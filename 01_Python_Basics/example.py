from openai import OpenAI
client = OpenAI(api_key="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")

response = client.responses.create(
    model="gpt-5",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)