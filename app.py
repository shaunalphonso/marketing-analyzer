import streamlit as st
import os
import time
import pandas as pd
import re
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI

# Page configuration
st.set_page_config(
    page_title="AI Marketing Analyzer | Shaun Alphonso",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6C757D;
        text-align: center;
        margin-bottom: 3rem;
        font-style: italic;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px 0;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    .recommendation-card {
        background: #F8F9FA;
        border-left: 4px solid #2E86AB;
        padding: 20px;
        margin: 15px 0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-message {
        background: #D4EDDA;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #28A745;
        margin: 10px 0;
    }
    .error-message {
        background: #F8D7DA;
        color: #721C24;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #DC3545;
        margin: 10px 0;
    }
    .footer {
        text-align: center;
        padding: 30px;
        color: #6C757D;
        font-style: italic;
        border-top: 2px solid #E9ECEF;
        margin-top: 50px;
    }
    .demo-badge {
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class WebsiteAnalyzer:
    """Main class for website analysis functionality."""
    
    def __init__(self):
        self.setup_selenium()
        self.setup_openai()
    
    def setup_selenium(self):
        """Configure Chrome browser for web scraping."""
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")  # Run in background
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--window-size=1920,1080")
    
    def setup_openai(self):
        """Setup OpenAI client with API key."""
        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("🚨 OpenAI API key not found! Please add it to your Streamlit secrets.")
            st.stop()
        self.openai_client = OpenAI(api_key=api_key)
    
    @st.cache_data(ttl=3600)  # Cache results for 1 hour
    def scrape_website(_self, url: str) -> str:
        """Extract content from website using Chrome browser."""
        try:
            # Setup Chrome driver automatically
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=_self.chrome_options)
            
            # Load the webpage
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract text content
            body_element = driver.find_element(By.TAG_NAME, "body")
            content = body_element.text.strip() if body_element else ""
            
            driver.quit()
            return content
            
        except Exception as e:
            return f"Error extracting content: {str(e)}"
    
    def analyze_content(self, content: str, url: str) -> dict:
        """Analyze website content using AI."""
        
        if not content or "Error" in content:
            return {"error": content}
        
        # Limit content length for API efficiency
        if len(content) > 4000:
            content = content[:4000] + "... [content truncated]"
        
        analysis_tasks = {
            "SEO Keywords": "Extract the 8-10 most important SEO keywords from this website. Return only the keywords separated by commas, no explanations:",
            "Marketing Strategy": "Summarize the main marketing approach in 2-3 clear sentences:",
            "Target Audience": "Who is the primary target audience? Answer in 1-2 sentences:",
            "Value Proposition": "What is the unique value proposition? Answer in 1-2 sentences:",
            "Call-to-Actions": "List the main call-to-action phrases found on the site, separated by commas:",
            "Content Themes": "What are the 4-5 main content themes/topics? List them separated by commas:"
        }
        
        results = {"URL": url, "Content_Length": len(content)}
        
        for task_name, prompt in analysis_tasks.items():
            try:
                full_prompt = f"{prompt}\n\nWebsite content from {url}:\n{content}"
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a marketing analyst. Give concise, specific answers only."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=250,
                    temperature=0.3
                )
                
                results[task_name] = response.choices[0].message.content.strip()
                
            except Exception as e:
                results[task_name] = f"Analysis error: {str(e)}"
        
        return results
    
    def generate_recommendations(self, analysis: dict) -> dict:
        """Generate marketing recommendations based on analysis."""
        
        # Prepare analysis summary
        analysis_text = "\n".join([f"{k}: {v}" for k, v in analysis.items() 
                                 if k not in ["URL", "Content_Length", "error"]])
        
        recommendation_areas = {
            "🎯 SEO Improvements": "Based on this website analysis, provide 3 specific SEO improvement recommendations. Be actionable and specific:",
            "📝 Content Strategy": "Suggest 3 content marketing strategies to improve engagement and reach:",
            "💼 User Experience": "Recommend 3 UX improvements to enhance user experience and navigation:",
            "📈 Conversion Optimization": "Provide 3 conversion rate optimization recommendations to improve results:"
        }
        
        recommendations = {}
        
        for area, prompt in recommendation_areas.items():
            try:
                full_prompt = f"{prompt}\n\nWebsite Analysis:\n{analysis_text}"
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a senior digital marketing consultant. Provide specific, actionable recommendations in bullet points."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=400,
                    temperature=0.5
                )
                
                recommendations[area] = response.choices[0].message.content.strip()
                
            except Exception as e:
                recommendations[area] = f"Error: {str(e)}"
        
        return recommendations

def main():
    """Main application function."""
    
    # Header section
    st.markdown('<h1 class="main-header">🚀 AI Marketing Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professional website analysis and marketing recommendations powered by AI</p>', unsafe_allow_html=True)
    
    # Demo badge
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div style="text-align: center;"><span class="demo-badge">💼 PORTFOLIO DEMO</span></div>', unsafe_allow_html=True)
    
    # Initialize analyzer
    if 'analyzer' not in st.session_state:
        with st.spinner("🔧 Initializing AI marketing analyzer..."):
            st.session_state.analyzer = WebsiteAnalyzer()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🎯 Website Analysis")
        
        # URL input
        url = st.text_input(
            "Enter Website URL:",
            placeholder="https://example.com",
            help="Enter any website URL for comprehensive marketing analysis"
        )
        
        # Analysis button
        analyze_button = st.button("🔍 Analyze Website", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        # What we analyze
        st.markdown("### 📋 Analysis Features:")
        features = [
            "🔍 SEO keyword identification",
            "📊 Marketing strategy analysis", 
            "👥 Target audience insights",
            "💡 Value proposition review",
            "🎯 Call-to-action audit",
            "📝 Content theme analysis",
            "🚀 Growth recommendations"
        ]
        
        for feature in features:
            st.markdown(f"- {feature}")
        
        st.markdown("---")
        
        # Quick examples
        st.markdown("### 🌟 Try These Examples:")
        example_sites = {
            "Stripe (Fintech)": "https://stripe.com",
            "Airbnb (Travel)": "https://airbnb.com",
            "Shopify (E-commerce)": "https://shopify.com"
        }
        
        for name, example_url in example_sites.items():
            if st.button(f"📱 {name}", key=f"example_{name}", use_container_width=True):
                st.session_state.example_url = example_url
                st.rerun()
    
    # Handle example URL selection
    if hasattr(st.session_state, 'example_url'):
        url = st.session_state.example_url
        delattr(st.session_state, 'example_url')
        analyze_button = True
    
    # Main content area
    if analyze_button and url:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Progress tracking
        progress_container = st.container()
        
        with progress_container:
            st.markdown("### 🔄 Analysis in Progress")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Web scraping
                status_text.success("🕷️ Step 1: Extracting website content...")
                progress_bar.progress(25)
                
                content = st.session_state.analyzer.scrape_website(url)
                time.sleep(1)  # Brief pause for user experience
                
                # Step 2: AI Analysis
                status_text.success("🧠 Step 2: AI analysis in progress...")
                progress_bar.progress(50)
                
                analysis_results = st.session_state.analyzer.analyze_content(content, url)
                
                if "error" in analysis_results:
                    st.error(f"❌ Analysis failed: {analysis_results['error']}")
                    return
                
                time.sleep(1)
                
                # Step 3: Generate recommendations
                status_text.success("💡 Step 3: Generating marketing recommendations...")
                progress_bar.progress(75)
                
                recommendations = st.session_state.analyzer.generate_recommendations(analysis_results)
                
                # Step 4: Complete
                status_text.success("✅ Step 4: Analysis complete!")
                progress_bar.progress(100)
                time.sleep(1)
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Display results
                st.markdown("---")
                st.markdown("## 📊 Analysis Results")
                
                # Key metrics overview
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    keywords = analysis_results.get("SEO Keywords", "").split(",")
                    keyword_count = len([k for k in keywords if k.strip()])
                    st.markdown(f'<div class="metric-container"><h3>🔍 SEO Keywords</h3><h2>{keyword_count}</h2><p>Keywords identified</p></div>', unsafe_allow_html=True)
                
                with col2:
                    ctas = analysis_results.get("Call-to-Actions", "").split(",")
                    cta_count = len([c for c in ctas if c.strip()])
                    st.markdown(f'<div class="metric-container"><h3>🎯 Call-to-Actions</h3><h2>{cta_count}</h2><p>CTAs found</p></div>', unsafe_allow_html=True)
                
                with col3:
                    content_length = analysis_results.get("Content_Length", 0)
                    st.markdown(f'<div class="metric-container"><h3>📄 Content Volume</h3><h2>{content_length:,}</h2><p>Characters analyzed</p></div>', unsafe_allow_html=True)
                
                # Detailed analysis results
                st.markdown("### 📈 Detailed Analysis")
                
                for key, value in analysis_results.items():
                    if key not in ["URL", "Content_Length", "error"] and not value.startswith("Analysis error"):
                        st.markdown(f"**{key}:**")
                        st.info(value)
                
                # AI Recommendations
                st.markdown("### 🚀 AI Marketing Recommendations")
                
                rec_cols = st.columns(2)
                col_index = 0
                
                for category, recommendations_text in recommendations.items():
                    with rec_cols[col_index % 2]:
                        st.markdown(f"#### {category}")
                        st.markdown(f'<div class="recommendation-card">{recommendations_text}</div>', unsafe_allow_html=True)
                    col_index += 1
                
                # Export functionality
                st.markdown("### 📥 Export Results")
                
                export_data = {
                    "website_url": url,
                    "analysis_results": analysis_results,
                    "recommendations": recommendations,
                    "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "analyzed_by": "AI Marketing Analyzer - Shaun Alphonso Portfolio"
                }
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        "📊 Download JSON Report",
                        data=json.dumps(export_data, indent=2),
                        file_name=f"marketing_analysis_{url.replace('https://', '').replace('/', '_')[:50]}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col2:
                    # Create simple CSV
                    df = pd.DataFrame([analysis_results])
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        "📈 Download CSV Data",
                        data=csv_data,
                        file_name=f"analysis_data_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                # Success message
                st.markdown('<div class="success-message">🎉 <strong>Analysis Complete!</strong> Your comprehensive marketing report is ready. Use the recommendations above to optimize your website\'s performance.</div>', unsafe_allow_html=True)
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.markdown(f'<div class="error-message">❌ <strong>Analysis Failed:</strong> {str(e)}<br><br>Please try again or contact support if the issue persists.</div>', unsafe_allow_html=True)
    
    elif analyze_button and not url:
        st.warning("⚠️ Please enter a website URL to begin analysis.")
    
    else:
        # Welcome message when no analysis is running
        st.markdown("### 👋 Welcome to the AI Marketing Analyzer")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("""
            This tool demonstrates advanced capabilities in:
            
            - **🤖 AI Integration**: OpenAI GPT-4 for intelligent content analysis
            - **🕷️ Web Scraping**: Automated data extraction using Selenium
            - **📊 Data Processing**: Real-time analysis and insights generation
            - **💼 Marketing Strategy**: Professional-grade recommendations
            - **🚀 Web Development**: Production-ready Streamlit application
            
            Enter any website URL in the sidebar to begin your analysis!
            """)
        
        with col2:
            st.info("""
            **💡 Built by Shaun Alphonso**
            
            This demo showcases technical expertise in AI/ML engineering, web development, and digital marketing strategy.
            
            **Technologies Used:**
            - Python, Streamlit
            - OpenAI API, Selenium
            - Docker, Cloud Deployment
            
            [📧 Contact](mailto:contact@shaunalphonso.com) | [🌐 Portfolio](https://shaunalphonso.com)
            """)
    
    # Footer
    st.markdown('<div class="footer">Built with ❤️ by <strong>Shaun Alphonso</strong> | Showcasing AI/ML Engineering & Digital Marketing Expertise<br>🚀 <em>This tool is part of my professional portfolio demonstrating production-ready AI applications</em></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()