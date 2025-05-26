import requests
from bs4 import BeautifulSoup

def fetch_jfk_archives(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch the page, status code: {response.status_code}")
        return None
    print(response.text)
    soup = BeautifulSoup(response.content, 'html.parser')

    #todo 找到页面主要内容区域
    content = soup.find('div', {'class': 'region-content'})

    if not content:
        print("Content not found.")
        return None

    # 提取所有段落内容
    paragraphs = content.find_all('p')
    text_content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

    return text_content


if __name__ == "__main__":
    url = "https://x.com/elonmusk"
    content = fetch_jfk_archives(url)

    if content:
        with open("jfk_archives.txt", "w", encoding="utf-8") as file:
            file.write(content)
        print("Content has been saved to jfk_archives.txt")
