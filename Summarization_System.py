import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from googlesearch import search
import fitz  # PyMuPDF for handling PDFs
from langchain_openai import AzureChatOpenAI

def initialize_azure_chat_openai():
    os.environ['OPENAI_API_KEY'] = "Insert API key"
    os.environ['AZURE_OPENAI_ENDPOINT'] = "Insert Endpoint"
    return AzureChatOpenAI(azure_deployment="gpt-35-turbo-16k", openai_api_version="2023-09-01-preview", temperature=0.1, streaming=True)

def fetch_top_links(query, company_name):
    try:
        search_query = f"{query} official site {company_name}"
        search_results = search(search_query, num=5, stop=5, pause=2)
        return list(search_results)
    except Exception as e:
        print(f"Failed to fetch top links for {query}: {e}")
        return []

def setup_selenium():
    options = Options()
    options.headless = True  # Runs Chrome in headless mode.
    driver = webdriver.Chrome(options=options)
    return driver

def scrape_text_with_selenium(url):
    driver = setup_selenium()
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.TAG_NAME, "body")))
        page_content = driver.find_element(By.TAG_NAME, "body").text
        return ' '.join(page_content.split())
    except Exception as e:
        print(f"Error fetching content from {url} using Selenium: {e}")
        return ""
    finally:
        driver.quit()

def extract_text_from_pdf(url):
    response = requests.get(url)
    with open("temp.pdf", "wb") as f:
        f.write(response.content)
    doc = fitz.open("temp.pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    os.remove("temp.pdf")
    return text

def fetch_content_from_url(url):
    if url.lower().endswith(".pdf"):
        return extract_text_from_pdf(url)
    else:
        return scrape_text_with_selenium(url)

def summarize_content(content):
    azure_llm = initialize_azure_chat_openai()
    messages = [SystemMessage(content=f"Summarize this text: {content[:16000]}")]
    response = azure_llm.invoke(messages)
    return response.content  # Assuming response.content retrieves the summary

def main(query, company_name, custom_url=""):
    output = ""
    individual_summaries = []
    if custom_url:
        content = fetch_content_from_url(custom_url)
        summary = summarize_content(content)
        output = f"Summary of custom URL ({custom_url}):\n{summary}"
    else:
        top_links = fetch_top_links(query, company_name)
        summaries = []
        for i, link in enumerate(top_links):
            content = fetch_content_from_url(link)
            if content:
                summary = summarize_content(content)
                summaries.append(summary)
                individual_summaries.append(f"Summary of link {i + 1}:\n{link}\n{summary}\n\n")
        if summaries:
            collective_content = " ".join(summaries)
            collective_summary = summarize_content(collective_content)
            output = f"Collective summary of all the links:\n{collective_summary}"
    return '\n'.join(individual_summaries) + output

# Set up Gradio interface to display the formatted output
iface = gr.Interface(fn=main,
                     inputs=["text", "text", "text"],
                     outputs="text",
                     title="Summarization System",
                     description="Enter your query and the company name to get summarized content from the official site of the company or directly input a URL.")
iface.launch(share='true')
