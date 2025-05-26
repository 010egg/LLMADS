from pdf2image import convert_from_path
import pytesseract
import os
import re
import math


def clean_text(raw_text: str) -> str:
    """
    对 OCR 原始文本进行预处理和清洗：
    - 删除页眉页脚及页码标识（例如 --- Page 1 ---）
    - 替换常见 OCR 错误字符，例如将 "~" 替换为 "-"
    - 清理多余的空白字符和换行
    """
    cleaned = re.sub(r"---\s*Page\s*\d+\s*---", "", raw_text)
    cleaned = cleaned.replace("~", "-")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def split_into_pages(raw_text: str) -> list:
    """
    根据页码标识拆分文本。
    如果存在类似 '--- Page X ---' 的标识，则将文本拆分为多个页面内容列表，
    否则返回整体文本作为一个列表元素。
    """
    pages = re.split(r"---\s*Page\s*\d+\s*---", raw_text)
    pages = [page.strip() for page in pages if page.strip()]
    return pages if pages else [raw_text.strip()]


def assemble_documents(document_texts: list) -> str:
    """
    将多个文档的文本组装成统一格式：
    - 每个文档先按页拆分，按 "Page X: 内容" 进行标识
    - 每个文档之间使用明确的分隔符进行区分
    """
    assembled_docs = []
    for i, doc in enumerate(document_texts):
        pages = split_into_pages(doc)
        doc_lines = [f"[Document {i + 1}]"]
        for j, page in enumerate(pages):
            doc_lines.append(f"Page {j + 1}: {page}")
        assembled_docs.append("\n".join(doc_lines))
    return "\n---- Document Separator ----\n".join(assembled_docs)


def extract_text_from_pdf(pdf_path: str, lang: str = 'eng') -> str:
    """
    提取指定 PDF 文件中的文本。
    将 PDF 分解为多页，每页前加上页码标识，最后将所有页的文本拼接在一起。
    """
    images = convert_from_path(pdf_path, dpi=200)
    page_texts = []
    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image, lang=lang)
        page_texts.append(f"--- Page {i + 1} ---\n{text.strip()}")
    return "\n".join(page_texts)


def process_multiple_pdfs(num: int, pdf_dir: str, lang: str = 'eng', save_dir: str = 'data') -> list:
    """
    处理指定目录下所有 PDF 文件，每处理完一批文件就将该批次的结果保存为 save_dir 目录下的一个文件。

    参数：
      num: 预期的批次数量
      pdf_dir: PDF 文件所在目录
      lang: OCR 语言，可选 'eng' 或 'chi_sim' 等
      save_dir: 保存结果文件的目录
    返回：
      每一批的处理结果组成的列表
    """
    # 确保保存目录存在
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    pdf_files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    pdf_files.sort()  # 保证顺序一致
    total_files = len(pdf_files)

    # 计算每批次处理的文件数（向上取整）
    chunk_size = math.ceil(total_files / num)
    print(f"总共 {total_files} 个 PDF，每批处理 {chunk_size} 个 PDF，共 {num} 批（最后一批可能不足）")

    results = []  # 用于保存每个批次的结果（文本）
    batch_index = 1  # 批次计数器
    current_texts = []  # 当前批次的文本

    for idx, pdf_file in enumerate(pdf_files, start=1):
        text = extract_text_from_pdf(pdf_file, lang=lang)
        cleaned_text = clean_text(text)
        current_texts.append(cleaned_text)
        print(idx)
        # 当达到一个批次的大小时保存结果
        if idx % chunk_size == 0:
            batch_result = ";".join(current_texts)
            results.append(batch_result)
            # 统计字符数作为后缀
            char_count = len(batch_result)
            file_path = os.path.join(save_dir, f"batch_{batch_index}_{char_count}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(batch_result)
            print(f"批次 {batch_index} 已保存：{file_path}")
            batch_index += 1
            current_texts = []  # 重置当前批次列表

    # 处理剩余不足一批的文件
    if current_texts:
        batch_result = ";".join(current_texts)
        results.append(batch_result)
        char_count = len(batch_result)
        file_path = os.path.join(save_dir, f"batch_{batch_index}_{char_count}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(batch_result)
        print(f"批次 {batch_index} 已保存：{file_path}")

    return results


def main(pdf_dir: str, lang: str = 'eng', save_dir: str = 'data') -> dict:
    """
    主函数，返回处理结果字典，并将每批结果保存为文件。

    参数:
      pdf_dir: PDF 文件所在目录
      lang: OCR 语言，可选 'eng' 或 'chi_sim' 等
      save_dir: 保存结果文件的目录
    """
    num = 100  # 预期的批次数量
    result_batches = process_multiple_pdfs(num, pdf_dir, lang=lang, save_dir=save_dir)
    return {
        "result_batches": result_batches,
    }


if __name__ == '__main__':
    pdf_directory = '/Users/xionghaoqiang/AI/bas/pdfs'
    output = main(pdf_directory, lang='eng', save_dir='data1')
    # 示例：逐批打印结果
    for i, batch in enumerate(output["result_batches"], start=1):
        print(f"===== Batch {i} =====")
        print(batch)