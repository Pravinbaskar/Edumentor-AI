"""PDF generator for quiz results."""

import io
import logging
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger("edumentor.pdf_generator")


class QuizPDFGenerator:
    """Generate PDF reports for quiz results."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#20beff'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#20beff'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Info style
        self.styles.add(ParagraphStyle(
            name='InfoText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            fontName='Helvetica'
        ))
        
        # Feedback style
        self.styles.add(ParagraphStyle(
            name='Feedback',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
            spaceBefore=6,
            fontName='Helvetica-Oblique'
        ))
    
    def generate_quiz_result_pdf(
        self,
        student_name: str,
        subject: str,
        topic: str,
        difficulty: str,
        total_questions: int,
        correct_answers: int,
        score_percentage: float,
        questions_data: List[Dict[str, Any]],
        user_answers: List[int],
        date: str = None
    ) -> bytes:
        """Generate a PDF report for quiz results.
        
        Args:
            student_name: Name of the student
            subject: Subject of the quiz
            topic: Topic of the quiz
            difficulty: Difficulty level
            total_questions: Total number of questions
            correct_answers: Number of correct answers
            score_percentage: Score as percentage
            questions_data: List of question dictionaries
            user_answers: List of user's answer indices
            date: Date of the quiz (defaults to current date)
            
        Returns:
            PDF content as bytes
        """
        if date is None:
            date = datetime.now().strftime("%B %d, %Y")
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Title
        title = Paragraph("EduMentor Quiz Results", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Student Information
        info_data = [
            ['Student Name:', student_name],
            ['Subject:', subject.capitalize()],
            ['Topic:', topic.capitalize()],
            ['Difficulty:', difficulty.capitalize()],
            ['Date:', date],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#20beff')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Score Summary
        score_heading = Paragraph("Score Summary", self.styles['CustomHeading'])
        elements.append(score_heading)
        
        # Determine feedback based on score
        feedback = self._generate_feedback(score_percentage)
        
        score_data = [
            ['Total Questions:', str(total_questions)],
            ['Correct Answers:', str(correct_answers)],
            ['Incorrect Answers:', str(total_questions - correct_answers)],
            ['Score:', f"{score_percentage:.1f}%"],
        ]
        
        score_table = Table(score_data, colWidths=[2*inch, 2*inch])
        score_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#20beff')),
            ('TEXTCOLOR', (1, 3), (1, 3), self._get_score_color(score_percentage)),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f0f0f0')),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Feedback
        feedback_para = Paragraph(f"<b>Feedback:</b> {feedback}", self.styles['Feedback'])
        elements.append(feedback_para)
        elements.append(Spacer(1, 0.3*inch))
        
        # Detailed Results
        details_heading = Paragraph("Detailed Results", self.styles['CustomHeading'])
        elements.append(details_heading)
        elements.append(Spacer(1, 0.1*inch))
        
        # Question by question breakdown
        for idx, (question, user_answer_idx) in enumerate(zip(questions_data, user_answers), 1):
            correct_idx = question['correct_answer']
            is_correct = user_answer_idx == correct_idx
            
            # Question number and text
            q_text = Paragraph(f"<b>Question {idx}:</b> {question['question']}", 
                             self.styles['InfoText'])
            elements.append(q_text)
            elements.append(Spacer(1, 0.05*inch))
            
            # Options with marking
            options_data = []
            for opt_idx, option in enumerate(question['options']):
                marker = ""
                text_color = colors.black
                
                if opt_idx == correct_idx:
                    marker = "✓ "
                    text_color = colors.green
                elif opt_idx == user_answer_idx and not is_correct:
                    marker = "✗ "
                    text_color = colors.red
                
                options_data.append([f"{marker}{chr(65 + opt_idx)}. {option}"])
            
            options_table = Table(options_data, colWidths=[5.5*inch])
            options_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            # Color the correct and incorrect answers
            for opt_idx in range(len(question['options'])):
                if opt_idx == correct_idx:
                    options_table.setStyle(TableStyle([
                        ('TEXTCOLOR', (0, opt_idx), (0, opt_idx), colors.green),
                        ('FONTNAME', (0, opt_idx), (0, opt_idx), 'Helvetica-Bold'),
                    ]))
                elif opt_idx == user_answer_idx and not is_correct:
                    options_table.setStyle(TableStyle([
                        ('TEXTCOLOR', (0, opt_idx), (0, opt_idx), colors.red),
                    ]))
            
            elements.append(options_table)
            elements.append(Spacer(1, 0.05*inch))
            
            # Explanation
            explanation = Paragraph(f"<i>Explanation: {question['explanation']}</i>", 
                                  self.styles['InfoText'])
            elements.append(explanation)
            elements.append(Spacer(1, 0.15*inch))
        
        # Footer
        elements.append(Spacer(1, 0.3*inch))
        footer = Paragraph(
            f"Generated by EduMentor on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            self.styles['Normal']
        )
        elements.append(footer)
        
        # Build PDF
        doc.build(elements)
        
        # Get the PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated PDF report for {student_name}: {score_percentage:.1f}%")
        return pdf_data
    
    def _generate_feedback(self, score_percentage: float) -> str:
        """Generate feedback based on score."""
        if score_percentage >= 90:
            return "Outstanding performance! You have mastered this topic."
        elif score_percentage >= 75:
            return "Great job! You have a strong understanding of the material."
        elif score_percentage >= 60:
            return "Good effort! Review the explanations to strengthen your understanding."
        elif score_percentage >= 40:
            return "Keep practicing! Focus on the areas where you made mistakes."
        else:
            return "Don't give up! Review the material and try again. You can do it!"
    
    def _get_score_color(self, score_percentage: float) -> colors.Color:
        """Get color based on score percentage."""
        if score_percentage >= 75:
            return colors.green
        elif score_percentage >= 60:
            return colors.HexColor('#FFA500')  # Orange
        else:
            return colors.red


# Global instance
pdf_generator = QuizPDFGenerator()
