import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

def fetch_jfk_archives_and_pdfs(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch the page, status code: {response.status_code}")
        return None, []

    soup = BeautifulSoup(response.content, 'html.parser')

    # 找到页面主要内容区域
    content = soup.find('div', {'class': 'region-content'})
    if not content:
        print("Content not found.")
        return None, []

    # 提取文本内容（与之前逻辑一致）
    paragraphs = content.find_all('p')
    text_content = "\n".join(
        p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
    )

    # 提取所有与 PDF 相关的链接
    pdf_links = []
    for a_tag in content.find_all('a', href=True):
        href = a_tag['href']
        # 判断是否是 PDF
        if '.pdf' in href.lower():
            # urljoin 可以将相对路径转为完整URL
            full_pdf_url = urljoin(url, href)
            pdf_links.append(full_pdf_url)

    return text_content, pdf_links


if __name__ == "__main__":
    url = "https://www.archives.gov/research/jfk/release-2025"
    text_content, pdf_links = fetch_jfk_archives_and_pdfs(url)

    # 将正文内容写入到文件（若需要）
    if text_content:
        with open("jfk_archives.txt", "w", encoding="utf-8") as file:
            file.write(text_content)
        print("页面文本内容已保存到 jfk_archives.txt")

    # 下载所有 PDF 文件
    if pdf_links:
        # 若需要存放在特定目录，可以先创建目录
        download_dir = "pdfs"
        os.makedirs(download_dir, exist_ok=True)

        for pdf_url in pdf_links:
            # 取 PDF 文件名（以链接中最后的部分作为文件名）
            pdf_name = pdf_url.split('/')[-1]
            pdf_path = os.path.join(download_dir, pdf_name)

            try:
                print(f"正在下载: {pdf_url}")
                pdf_response = requests.get(pdf_url)
                if pdf_response.status_code == 200:
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_response.content)
                    print(f"下载完成: {pdf_path}")
                else:
                    print(f"下载失败，状态码: {pdf_response.status_code}")
            except Exception as e:
                print(f"下载出现错误: {e}")
    else:
        print("页面中未找到任何 PDF 链接。")