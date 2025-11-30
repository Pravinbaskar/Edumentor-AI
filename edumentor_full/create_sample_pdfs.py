"""
Create a sample PDF with text content for testing the vector database.
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import os

def create_sample_pdf(filename, subject):
    """Create a sample PDF with educational content."""
    
    content = {
        "maths": """
        Introduction to Algebra
        
        Algebra is a branch of mathematics that uses symbols and letters to represent numbers and quantities in formulas and equations.
        
        Basic Concepts:
        1. Variables: Letters like x, y, z represent unknown values
        2. Constants: Fixed numbers like 5, 10, 100
        3. Expressions: Combinations of variables and constants
        
        Addition and Subtraction:
        When solving equations, you can add or subtract the same number from both sides.
        Example: x + 5 = 12
        Solution: x = 12 - 5 = 7
        
        Multiplication and Division:
        The same principle applies to multiplication and division.
        Example: 3x = 15
        Solution: x = 15 / 3 = 5
        
        Practice Problems:
        1. Solve for x: 2x + 3 = 11
        2. Solve for y: 5y - 7 = 18
        3. Solve for z: z/4 = 6
        """,
        
        "science": """
        Photosynthesis: How Plants Make Food
        
        Photosynthesis is the process by which green plants use sunlight to make their own food.
        
        Requirements for Photosynthesis:
        1. Sunlight - provides energy
        2. Water - absorbed through roots
        3. Carbon dioxide - taken from air through stomata
        4. Chlorophyll - green pigment in leaves
        
        The Process:
        Plants capture sunlight using chlorophyll in their leaves. This energy is used to convert water and carbon dioxide into glucose (sugar) and oxygen.
        
        Chemical Equation:
        6CO2 + 6H2O + light energy → C6H12O6 + 6O2
        
        Importance:
        - Provides food for plants
        - Produces oxygen for animals and humans
        - Removes carbon dioxide from atmosphere
        - Foundation of food chains
        
        Key Terms:
        - Chloroplast: Organelle where photosynthesis occurs
        - Stomata: Tiny pores on leaves for gas exchange
        - Glucose: Sugar produced during photosynthesis
        """,
        
        "evs": """
        Environmental Conservation and Sustainability
        
        Environmental conservation is the protection and preservation of natural resources and ecosystems.
        
        Major Environmental Issues:
        1. Climate Change: Rising temperatures due to greenhouse gases
        2. Pollution: Contamination of air, water, and soil
        3. Deforestation: Loss of forest cover
        4. Loss of Biodiversity: Extinction of species
        
        Conservation Methods:
        - Reduce, Reuse, Recycle: Minimize waste
        - Plant Trees: Combat deforestation
        - Save Water: Conserve precious resources
        - Use Renewable Energy: Solar, wind, hydro power
        - Protect Wildlife: Preserve habitats
        
        Individual Actions:
        1. Turn off lights when not in use
        2. Use public transport or carpool
        3. Avoid single-use plastics
        4. Compost organic waste
        5. Support eco-friendly products
        
        Remember: Small changes in daily habits can make a big difference in protecting our planet for future generations.
        """
    }
    
    # Create PDF
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, height - 100, f"Sample {subject.upper()} Study Material")
    
    # Content
    c.setFont("Helvetica", 11)
    text = c.beginText(100, height - 150)
    text.setFont("Helvetica", 11)
    text.setLeading(14)
    
    for line in content[subject].split('\n'):
        text.textLine(line.strip())
    
    c.drawText(text)
    c.save()
    
    print(f"Created {filename}")

if __name__ == "__main__":
    os.makedirs("sample_pdfs", exist_ok=True)
    
    try:
        create_sample_pdf("sample_pdfs/maths_sample.pdf", "maths")
        create_sample_pdf("sample_pdfs/science_sample.pdf", "science")
        create_sample_pdf("sample_pdfs/evs_sample.pdf", "evs")
        print("\n✅ All sample PDFs created successfully!")
        print("\nYou can now upload these PDFs through the UI to test the vector database.")
    except ImportError:
        print("⚠️  reportlab not installed. Creating simple text files instead...")
        for subject in ["maths", "science", "evs"]:
            with open(f"sample_pdfs/{subject}_sample.txt", "w") as f:
                f.write(f"Sample content for {subject}")
        print("Created text files. Install reportlab with: pip install reportlab")
