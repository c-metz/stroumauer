import requests
from bs4 import BeautifulSoup


# Routine to download the latest Communautés énergétiques PDF from ILR
ilr_url = "https://www.ilr.lu/publications/liste-des-communautes-energetiques/"
pdf_filename = "ilr-elc-pub-Communautes-Energetiques.pdf"

try:
    page = requests.get(ilr_url)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "html.parser")
    # Find the download button/link for the PDF
    link = soup.find("a", string=lambda s: s and "Télécharger" in s)
    if not link:
        # Fallback: look for any PDF link on the page
        link = soup.find("a", href=lambda h: h and h.endswith(".pdf"))
    if link and link.has_attr("href"):
        pdf_download_url = link["href"]
        if not pdf_download_url.startswith("http"):
            pdf_download_url = "https://www.ilr.lu" + pdf_download_url
        response = requests.get(pdf_download_url)
        response.raise_for_status()
        with open("data/"+pdf_filename, "wb") as f:
            f.write(response.content)
        print(f"Downloaded latest Communautés énergétiques PDF to data/{pdf_filename}")
    else:
        print("Could not find PDF download link on ILR page.")
except Exception as e:
    print(f"Failed to download PDF: {e}")



