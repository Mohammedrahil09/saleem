'''import streamlit as st
import pandas as pd
import google.generativeai as genai

genai.configure(api_key="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")

model = genai.GenerativeModel("gemini-pro")

response = model.generate_content("Explain AI in one line")

print(response.text)'''