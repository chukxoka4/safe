from fpdf import FPDF

def generate_large_pdf(path, num_pages=100):
    pdf = FPDF()
    for i in range(num_pages):
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"This is page {i+1} of a large PDF for stress testing.", ln=True)
    pdf.output(path)

if __name__ == "__main__":
    generate_large_pdf("tests/sample_files/large_sample.pdf", num_pages=200)