import streamlit as st
import os
import time
import pandas as pd
import re
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from urllib.parse import urljoin, urlparse
import ssl
import urllib3

# Disable SSL warnings for demo purposes
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    .tech-note {
        background: #E3F2FD;
        border: 1px solid #2196F3;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

class WebsiteAnalyzer:
    """Streamlit-compatible website analyzer using requests + BeautifulSoup."""
    
    def __init__(self):
        self.setup_openai()
        self.setup_requests()
    
    def setup_requests(self):
        """Setup requests session with proper headers."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def setup_openai(self):
        """Setup OpenAI client with API key."""
        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("🚨 OpenAI API key not found! Please add it to your Streamlit secrets.")
            st.stop()
        self.openai_client = OpenAI(api_key=api_key)
    
    @st.cache_data(ttl=3600)  # Cache results for 1 hour
    def scrape_website(_self, url: str) -> dict:
        """Extract content from website using requests and BeautifulSoup."""
        try:
            # Make request with timeout
            response = _self.session.get(url, timeout=15, verify=False)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
            
            # Extract text content
            text_content = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_content = ' '.join(chunk for chunk in chunks if chunk)
            
            # Extract meta information
            title = soup.find('title')
            title_text = title.get_text() if title else "No title found"
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content') if meta_desc else "No description found"
            
            # Get headings
            headings = []
            for i in range(1, 4):  # h1, h2, h3
                for heading in soup.find_all(f'h{i}'):
                    headings.append(heading.get_text().strip())
            
            return {
                'success': True,
                'content': text_content,
                'title': title_text,
                'description': description,
                'headings': headings[:10],  # First 10 headings
                'content_length': len(text_content),
                'status_code': response.status_code
            }
            
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Website took too long to respond (timeout)'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Could not connect to website'}
        except requests.exceptions.HTTPError as e:
            return {'success': False, 'error': f'HTTP Error: {e.response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}
    
    def analyze_content(self, scrape_result: dict, url: str) -> dict:
        """Analyze website content using AI."""
        
        if not scrape_result['success']:
            return {"error": scrape_result['error']}
        
        content = scrape_result['content']
        title = scrape_result['title']
        description = scrape_result['description']
        headings = scrape_result['headings']
        
        # Limit content length for API efficiency
        if len(content) > 4000:
            content = content[:4000] + "... [content truncated for analysis]"
        
        # Prepare structured content for analysis
        structured_content = f"""
        Website: {url}
        Title: {title}
        Meta Description: {description}
        Main Headings: {', '.join(headings)}
        
        Content:
        {content}
        """
        
        analysis_tasks = {
            "SEO Keywords": "Extract the 8-10 most important SEO keywords from this website. Focus on terms the site is trying to rank for. Return only keywords separated by commas:",
            "Marketing Strategy": "What is the main marketing strategy or approach? Summarize in 2-3 clear sentences:",
            "Target Audience": "Who is the primary target audience based on the content and messaging? Answer in 1-2 sentences:",
            "Value Proposition": "What is the main value proposition or unique selling point? Answer in 1-2 sentences:",
            "Call-to-Actions": "List the main call-to-action phrases or buttons found. Separate with commas:",
            "Business Type": "What type of business is this? (e.g., SaaS, E-commerce, Agency, etc.) Answer briefly:",
            "Content Themes": "What are the 4-5 main content themes or topics covered? List separated by commas:"
        }
        
        results = {
            "URL": url, 
            "Title": title,
            "Content_Length": len(scrape_result['content'])
        }
        
        for task_name, prompt in analysis_tasks.items():
            try:
                full_prompt = f"{prompt}\n\n{structured_content}"
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a digital marketing analyst. Provide concise, specific, and actionable insights. Focus on what's actually present in the content."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=200,
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
                                 if k not in ["URL", "Title", "Content_Length", "error"]])
        
        recommendation_areas = {
            "🔍 SEO Optimization": "Based on this website analysis, provide 3 specific and actionable SEO improvements. Focus on technical SEO, content optimization, and keyword strategy:",
            "📝 Content Marketing": "Suggest 3 content marketing strategies to improve engagement and attract more visitors:",
            "💼 User Experience": "Recommend 3 UX improvements to enhance user experience and reduce bounce rate:",
            "📈 Conversion Optimization": "Provide 3 conversion rate optimization recommendations to improve lead generation or sales:"
        }
        
        recommendations = {}
        
        for area, prompt in recommendation_areas.items():
            try:
                full_prompt = f"{prompt}\n\nWebsite Analysis:\n{analysis_text}"
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a senior digital marketing consultant with expertise in SEO, content marketing, and conversion optimization. Provide specific, actionable recommendations that can be implemented immediately."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=350,
                    temperature=0.5
                )
                
                recommendations[area] = response.choices[0].message.content.strip()
                
            except Exception as e:
                recommendations[area] = f"Error generating recommendations: {str(e)}"
        
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
    
    # Technical note
    st.markdown('<div class="tech-note">🔧 <strong>Technical Note:</strong> This version uses Python requests + BeautifulSoup for web scraping, optimized for Streamlit Cloud deployment. Perfect for analyzing most websites including SPAs and modern sites.</div>', unsafe_allow_html=True)
    
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
            "🔍 SEO keyword extraction",
            "📊 Marketing strategy analysis", 
            "👥 Target audience insights",
            "💡 Value proposition review",
            "🎯 Call-to-action identification",
            "🏢 Business type classification",
            "📝 Content theme analysis",
            "🚀 Actionable recommendations"
        ]
        
        for feature in features:
            st.markdown(f"- {feature}")
        
        st.markdown("---")
        
        # Quick examples
        st.markdown("### 🌟 Try These Examples:")
        example_sites = {
            "Stripe (Fintech)": "https://stripe.com",
            "Shopify (E-commerce)": "https://shopify.com",
            "Mailchimp (Marketing)": "https://mailchimp.com",
            "Notion (Productivity)": "https://notion.so"
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
                status_text.success("🌐 Step 1: Extracting website content...")
                progress_bar.progress(25)
                
                scrape_result = st.session_state.analyzer.scrape_website(url)
                time.sleep(1)
                
                # Step 2: AI Analysis
                status_text.success("🧠 Step 2: AI analysis in progress...")
                progress_bar.progress(50)
                
                analysis_results = st.session_state.analyzer.analyze_content(scrape_result, url)
                
                if "error" in analysis_results:
                    st.error(f"❌ Analysis failed: {analysis_results['error']}")
                    st.info("💡 **Troubleshooting Tips:**\n- Make sure the URL is correct and accessible\n- Some websites block automated requests\n- Try a different website or check if the site is down")
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
                    keyword_count = len([k for k in keywords if k.strip() and len(k.strip()) > 2])
                    st.markdown(f'<div class="metric-container"><h3>🔍 SEO Keywords</h3><h2>{keyword_count}</h2><p>Keywords identified</p></div>', unsafe_allow_html=True)
                
                with col2:
                    ctas = analysis_results.get("Call-to-Actions", "").split(",")
                    cta_count = len([c for c in ctas if c.strip() and len(c.strip()) > 3])
                    st.markdown(f'<div class="metric-container"><h3>🎯 Call-to-Actions</h3><h2>{cta_count}</h2><p>CTAs found</p></div>', unsafe_allow_html=True)
                
                with col3:
                    content_length = analysis_results.get("Content_Length", 0)
                    st.markdown(f'<div class="metric-container"><h3>📄 Content Volume</h3><h2>{content_length:,}</h2><p>Characters analyzed</p></div>', unsafe_allow_html=True)
                
                # Detailed analysis results
                st.markdown("### 📈 Detailed Analysis")
                
                # Display in a more organized way
                analysis_display_order = [
                    "Business Type", "Target Audience", "Value Proposition", 
                    "Marketing Strategy", "SEO Keywords", "Call-to-Actions", "Content Themes"
                ]
                
                for key in analysis_display_order:
                    if key in analysis_results and not str(analysis_results[key]).startswith("Analysis error"):
                        st.markdown(f"**{key}:**")
                        st.info(analysis_results[key])
                
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
                    "website_title": analysis_results.get("Title", ""),
                    "analysis_results": analysis_results,
                    "recommendations": recommendations,
                    "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "analyzed_by": "AI Marketing Analyzer - Shaun Alphonso Portfolio",
                    "tool_version": "2.0 - Streamlit Optimized"
                }
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        "📊 Download Full Report (JSON)",
                        data=json.dumps(export_data, indent=2),
                        file_name=f"marketing_analysis_{url.replace('https://', '').replace('/', '_')[:50]}_{time.strftime('%Y%m%d')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col2:
                    # Create summary CSV
                    summary_data = {
                        "Website": [url],
                        "Title": [analysis_results.get("Title", "")],
                        "Business_Type": [analysis_results.get("Business Type", "")],
                        "SEO_Keywords": [analysis_results.get("SEO Keywords", "")],
                        "Target_Audience": [analysis_results.get("Target Audience", "")],
                        "Content_Length": [analysis_results.get("Content_Length", 0)]
                    }
                    df = pd.DataFrame(summary_data)
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        "📈 Download Summary (CSV)",
                        data=csv_data,
                        file_name=f"analysis_summary_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                # Success message
                st.markdown('<div class="success-message">🎉 <strong>Analysis Complete!</strong> Your comprehensive marketing report is ready. The recommendations above are tailored specifically for this website and can be implemented immediately.</div>', unsafe_allow_html=True)
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.markdown(f'<div class="error-message">❌ <strong>Analysis Failed:</strong> {str(e)}<br><br>This might be due to the website blocking automated requests or network issues. Please try a different website or try again later.</div>', unsafe_allow_html=True)
    
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
            - **🌐 Web Scraping**: Automated data extraction using Python requests & BeautifulSoup
            - **📊 Data Processing**: Real-time analysis and insights generation
            - **💼 Marketing Strategy**: Professional-grade recommendations
            - **🚀 Web Development**: Production-ready Streamlit application
            - **☁️ Cloud Deployment**: Optimized for Streamlit Cloud infrastructure
            
            **Ready to analyze?** Enter any website URL in the sidebar to begin your comprehensive marketing analysis!
            """)
        
        with col2:
            st.info("""
            **💡 Built by Shaun Alphonso**
            
            This demo showcases technical expertise in AI/ML engineering, web development, and digital marketing strategy.
            
            **Technologies Used:**
            - Python, Streamlit
            - OpenAI GPT-4o-mini API
            - Requests, BeautifulSoup
            - Cloud deployment optimization
            
            **Perfect for analyzing:**
            - SaaS websites
            - E-commerce stores  
            - Marketing agencies
            - Corporate websites
            - Landing pages
            
            [📧 Contact](mailto:contact@shaunalphonso.com) | [🌐 Portfolio](https://shaunalphonso.com)
            """)
    
    # Footer
    st.markdown('<div class="footer">Built with ❤️ by <strong>Shaun Alphonso</strong> | Showcasing AI/ML Engineering & Digital Marketing Expertise<br>🔧 <em>Optimized for Streamlit Cloud • No Selenium dependencies • Production-ready architecture</em></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()



# import streamlit as st
# import os
# import time
# import pandas as pd
# import re
# import json
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
# from openai import OpenAI

# # Page configuration
# st.set_page_config(
#     page_title="AI Marketing Analyzer | Shaun Alphonso",
#     page_icon="🚀",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS styling
# st.markdown("""
# <style>
#     .main-header {
#         font-size: 3rem;
#         color: #2E86AB;
#         text-align: center;
#         margin-bottom: 2rem;
#         text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
#     }
#     .sub-header {
#         font-size: 1.2rem;
#         color: #6C757D;
#         text-align: center;
#         margin-bottom: 3rem;
#         font-style: italic;
#     }
#     .metric-container {
#         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#         padding: 20px;
#         border-radius: 15px;
#         color: white;
#         margin: 10px 0;
#         box-shadow: 0 8px 16px rgba(0,0,0,0.1);
#     }
#     .recommendation-card {
#         background: #F8F9FA;
#         border-left: 4px solid #2E86AB;
#         padding: 20px;
#         margin: 15px 0;
#         border-radius: 8px;
#         box-shadow: 0 2px 4px rgba(0,0,0,0.1);
#     }
#     .success-message {
#         background: #D4EDDA;
#         color: #155724;
#         padding: 15px;
#         border-radius: 8px;
#         border-left: 4px solid #28A745;
#         margin: 10px 0;
#     }
#     .error-message {
#         background: #F8D7DA;
#         color: #721C24;
#         padding: 15px;
#         border-radius: 8px;
#         border-left: 4px solid #DC3545;
#         margin: 10px 0;
#     }
#     .footer {
#         text-align: center;
#         padding: 30px;
#         color: #6C757D;
#         font-style: italic;
#         border-top: 2px solid #E9ECEF;
#         margin-top: 50px;
#     }
#     .demo-badge {
#         background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
#         color: white;
#         padding: 5px 15px;
#         border-radius: 20px;
#         font-size: 0.8rem;
#         font-weight: bold;
#     }
# </style>
# """, unsafe_allow_html=True)

# class WebsiteAnalyzer:
#     """Main class for website analysis functionality."""
    
#     def __init__(self):
#         self.setup_selenium()
#         self.setup_openai()
    
#     def setup_selenium(self):
#         """Configure Chrome browser for web scraping."""
#         self.chrome_options = Options()
#         self.chrome_options.add_argument("--headless")  # Run in background
#         self.chrome_options.add_argument("--disable-gpu")
#         self.chrome_options.add_argument("--no-sandbox")
#         self.chrome_options.add_argument("--disable-dev-shm-usage")
#         self.chrome_options.add_argument("--window-size=1920,1080")
    
#     def setup_openai(self):
#         """Setup OpenAI client with API key."""
#         api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
#         if not api_key:
#             st.error("🚨 OpenAI API key not found! Please add it to your Streamlit secrets.")
#             st.stop()
#         self.openai_client = OpenAI(api_key=api_key)
    
#     @st.cache_data(ttl=3600)  # Cache results for 1 hour
#     def scrape_website(_self, url: str) -> str:
#         """Extract content from website using Chrome browser."""
#         try:
#             # Setup Chrome driver automatically
#             service = Service(ChromeDriverManager().install())
#             driver = webdriver.Chrome(service=service, options=_self.chrome_options)
            
#             # Load the webpage
#             driver.get(url)
#             WebDriverWait(driver, 15).until(
#                 EC.presence_of_element_located((By.TAG_NAME, "body"))
#             )
            
#             # Extract text content
#             body_element = driver.find_element(By.TAG_NAME, "body")
#             content = body_element.text.strip() if body_element else ""
            
#             driver.quit()
#             return content
            
#         except Exception as e:
#             return f"Error extracting content: {str(e)}"
    
#     def analyze_content(self, content: str, url: str) -> dict:
#         """Analyze website content using AI."""
        
#         if not content or "Error" in content:
#             return {"error": content}
        
#         # Limit content length for API efficiency
#         if len(content) > 4000:
#             content = content[:4000] + "... [content truncated]"
        
#         analysis_tasks = {
#             "SEO Keywords": "Extract the 8-10 most important SEO keywords from this website. Return only the keywords separated by commas, no explanations:",
#             "Marketing Strategy": "Summarize the main marketing approach in 2-3 clear sentences:",
#             "Target Audience": "Who is the primary target audience? Answer in 1-2 sentences:",
#             "Value Proposition": "What is the unique value proposition? Answer in 1-2 sentences:",
#             "Call-to-Actions": "List the main call-to-action phrases found on the site, separated by commas:",
#             "Content Themes": "What are the 4-5 main content themes/topics? List them separated by commas:"
#         }
        
#         results = {"URL": url, "Content_Length": len(content)}
        
#         for task_name, prompt in analysis_tasks.items():
#             try:
#                 full_prompt = f"{prompt}\n\nWebsite content from {url}:\n{content}"
                
#                 response = self.openai_client.chat.completions.create(
#                     model="gpt-4o-mini",
#                     messages=[
#                         {"role": "system", "content": "You are a marketing analyst. Give concise, specific answers only."},
#                         {"role": "user", "content": full_prompt}
#                     ],
#                     max_tokens=250,
#                     temperature=0.3
#                 )
                
#                 results[task_name] = response.choices[0].message.content.strip()
                
#             except Exception as e:
#                 results[task_name] = f"Analysis error: {str(e)}"
        
#         return results
    
#     def generate_recommendations(self, analysis: dict) -> dict:
#         """Generate marketing recommendations based on analysis."""
        
#         # Prepare analysis summary
#         analysis_text = "\n".join([f"{k}: {v}" for k, v in analysis.items() 
#                                  if k not in ["URL", "Content_Length", "error"]])
        
#         recommendation_areas = {
#             "🎯 SEO Improvements": "Based on this website analysis, provide 3 specific SEO improvement recommendations. Be actionable and specific:",
#             "📝 Content Strategy": "Suggest 3 content marketing strategies to improve engagement and reach:",
#             "💼 User Experience": "Recommend 3 UX improvements to enhance user experience and navigation:",
#             "📈 Conversion Optimization": "Provide 3 conversion rate optimization recommendations to improve results:"
#         }
        
#         recommendations = {}
        
#         for area, prompt in recommendation_areas.items():
#             try:
#                 full_prompt = f"{prompt}\n\nWebsite Analysis:\n{analysis_text}"
                
#                 response = self.openai_client.chat.completions.create(
#                     model="gpt-4o-mini",
#                     messages=[
#                         {"role": "system", "content": "You are a senior digital marketing consultant. Provide specific, actionable recommendations in bullet points."},
#                         {"role": "user", "content": full_prompt}
#                     ],
#                     max_tokens=400,
#                     temperature=0.5
#                 )
                
#                 recommendations[area] = response.choices[0].message.content.strip()
                
#             except Exception as e:
#                 recommendations[area] = f"Error: {str(e)}"
        
#         return recommendations

# def main():
#     """Main application function."""
    
#     # Header section
#     st.markdown('<h1 class="main-header">🚀 AI Marketing Analyzer</h1>', unsafe_allow_html=True)
#     st.markdown('<p class="sub-header">Professional website analysis and marketing recommendations powered by AI</p>', unsafe_allow_html=True)
    
#     # Demo badge
#     col1, col2, col3 = st.columns([1, 2, 1])
#     with col2:
#         st.markdown('<div style="text-align: center;"><span class="demo-badge">💼 PORTFOLIO DEMO</span></div>', unsafe_allow_html=True)
    
#     # Initialize analyzer
#     if 'analyzer' not in st.session_state:
#         with st.spinner("🔧 Initializing AI marketing analyzer..."):
#             st.session_state.analyzer = WebsiteAnalyzer()
    
#     # Sidebar configuration
#     with st.sidebar:
#         st.header("🎯 Website Analysis")
        
#         # URL input
#         url = st.text_input(
#             "Enter Website URL:",
#             placeholder="https://example.com",
#             help="Enter any website URL for comprehensive marketing analysis"
#         )
        
#         # Analysis button
#         analyze_button = st.button("🔍 Analyze Website", type="primary", use_container_width=True)
        
#         st.markdown("---")
        
#         # What we analyze
#         st.markdown("### 📋 Analysis Features:")
#         features = [
#             "🔍 SEO keyword identification",
#             "📊 Marketing strategy analysis", 
#             "👥 Target audience insights",
#             "💡 Value proposition review",
#             "🎯 Call-to-action audit",
#             "📝 Content theme analysis",
#             "🚀 Growth recommendations"
#         ]
        
#         for feature in features:
#             st.markdown(f"- {feature}")
        
#         st.markdown("---")
        
#         # Quick examples
#         st.markdown("### 🌟 Try These Examples:")
#         example_sites = {
#             "Stripe (Fintech)": "https://stripe.com",
#             "Airbnb (Travel)": "https://airbnb.com",
#             "Shopify (E-commerce)": "https://shopify.com"
#         }
        
#         for name, example_url in example_sites.items():
#             if st.button(f"📱 {name}", key=f"example_{name}", use_container_width=True):
#                 st.session_state.example_url = example_url
#                 st.rerun()
    
#     # Handle example URL selection
#     if hasattr(st.session_state, 'example_url'):
#         url = st.session_state.example_url
#         delattr(st.session_state, 'example_url')
#         analyze_button = True
    
#     # Main content area
#     if analyze_button and url:
#         # Validate URL
#         if not url.startswith(('http://', 'https://')):
#             url = 'https://' + url
        
#         # Progress tracking
#         progress_container = st.container()
        
#         with progress_container:
#             st.markdown("### 🔄 Analysis in Progress")
#             progress_bar = st.progress(0)
#             status_text = st.empty()
            
#             try:
#                 # Step 1: Web scraping
#                 status_text.success("🕷️ Step 1: Extracting website content...")
#                 progress_bar.progress(25)
                
#                 content = st.session_state.analyzer.scrape_website(url)
#                 time.sleep(1)  # Brief pause for user experience
                
#                 # Step 2: AI Analysis
#                 status_text.success("🧠 Step 2: AI analysis in progress...")
#                 progress_bar.progress(50)
                
#                 analysis_results = st.session_state.analyzer.analyze_content(content, url)
                
#                 if "error" in analysis_results:
#                     st.error(f"❌ Analysis failed: {analysis_results['error']}")
#                     return
                
#                 time.sleep(1)
                
#                 # Step 3: Generate recommendations
#                 status_text.success("💡 Step 3: Generating marketing recommendations...")
#                 progress_bar.progress(75)
                
#                 recommendations = st.session_state.analyzer.generate_recommendations(analysis_results)
                
#                 # Step 4: Complete
#                 status_text.success("✅ Step 4: Analysis complete!")
#                 progress_bar.progress(100)
#                 time.sleep(1)
                
#                 # Clear progress indicators
#                 progress_bar.empty()
#                 status_text.empty()
                
#                 # Display results
#                 st.markdown("---")
#                 st.markdown("## 📊 Analysis Results")
                
#                 # Key metrics overview
#                 col1, col2, col3 = st.columns(3)
                
#                 with col1:
#                     keywords = analysis_results.get("SEO Keywords", "").split(",")
#                     keyword_count = len([k for k in keywords if k.strip()])
#                     st.markdown(f'<div class="metric-container"><h3>🔍 SEO Keywords</h3><h2>{keyword_count}</h2><p>Keywords identified</p></div>', unsafe_allow_html=True)
                
#                 with col2:
#                     ctas = analysis_results.get("Call-to-Actions", "").split(",")
#                     cta_count = len([c for c in ctas if c.strip()])
#                     st.markdown(f'<div class="metric-container"><h3>🎯 Call-to-Actions</h3><h2>{cta_count}</h2><p>CTAs found</p></div>', unsafe_allow_html=True)
                
#                 with col3:
#                     content_length = analysis_results.get("Content_Length", 0)
#                     st.markdown(f'<div class="metric-container"><h3>📄 Content Volume</h3><h2>{content_length:,}</h2><p>Characters analyzed</p></div>', unsafe_allow_html=True)
                
#                 # Detailed analysis results
#                 st.markdown("### 📈 Detailed Analysis")
                
#                 for key, value in analysis_results.items():
#                     if key not in ["URL", "Content_Length", "error"] and not value.startswith("Analysis error"):
#                         st.markdown(f"**{key}:**")
#                         st.info(value)
                
#                 # AI Recommendations
#                 st.markdown("### 🚀 AI Marketing Recommendations")
                
#                 rec_cols = st.columns(2)
#                 col_index = 0
                
#                 for category, recommendations_text in recommendations.items():
#                     with rec_cols[col_index % 2]:
#                         st.markdown(f"#### {category}")
#                         st.markdown(f'<div class="recommendation-card">{recommendations_text}</div>', unsafe_allow_html=True)
#                     col_index += 1
                
#                 # Export functionality
#                 st.markdown("### 📥 Export Results")
                
#                 export_data = {
#                     "website_url": url,
#                     "analysis_results": analysis_results,
#                     "recommendations": recommendations,
#                     "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
#                     "analyzed_by": "AI Marketing Analyzer - Shaun Alphonso Portfolio"
#                 }
                
#                 col1, col2 = st.columns(2)
                
#                 with col1:
#                     st.download_button(
#                         "📊 Download JSON Report",
#                         data=json.dumps(export_data, indent=2),
#                         file_name=f"marketing_analysis_{url.replace('https://', '').replace('/', '_')[:50]}.json",
#                         mime="application/json",
#                         use_container_width=True
#                     )
                
#                 with col2:
#                     # Create simple CSV
#                     df = pd.DataFrame([analysis_results])
#                     csv_data = df.to_csv(index=False)
#                     st.download_button(
#                         "📈 Download CSV Data",
#                         data=csv_data,
#                         file_name=f"analysis_data_{time.strftime('%Y%m%d_%H%M%S')}.csv",
#                         mime="text/csv",
#                         use_container_width=True
#                     )
                
#                 # Success message
#                 st.markdown('<div class="success-message">🎉 <strong>Analysis Complete!</strong> Your comprehensive marketing report is ready. Use the recommendations above to optimize your website\'s performance.</div>', unsafe_allow_html=True)
                
#             except Exception as e:
#                 progress_bar.empty()
#                 status_text.empty()
#                 st.markdown(f'<div class="error-message">❌ <strong>Analysis Failed:</strong> {str(e)}<br><br>Please try again or contact support if the issue persists.</div>', unsafe_allow_html=True)
    
#     elif analyze_button and not url:
#         st.warning("⚠️ Please enter a website URL to begin analysis.")
    
#     else:
#         # Welcome message when no analysis is running
#         st.markdown("### 👋 Welcome to the AI Marketing Analyzer")
        
#         col1, col2 = st.columns([3, 2])
        
#         with col1:
#             st.markdown("""
#             This tool demonstrates advanced capabilities in:
            
#             - **🤖 AI Integration**: OpenAI GPT-4 for intelligent content analysis
#             - **🕷️ Web Scraping**: Automated data extraction using Selenium
#             - **📊 Data Processing**: Real-time analysis and insights generation
#             - **💼 Marketing Strategy**: Professional-grade recommendations
#             - **🚀 Web Development**: Production-ready Streamlit application
            
#             Enter any website URL in the sidebar to begin your analysis!
#             """)
        
#         with col2:
#             st.info("""
#             **💡 Built by Shaun Alphonso**
            
#             This demo showcases technical expertise in AI/ML engineering, web development, and digital marketing strategy.
            
#             **Technologies Used:**
#             - Python, Streamlit
#             - OpenAI API, Selenium
#             - Docker, Cloud Deployment
            
#             [📧 Contact](mailto:contact@shaunalphonso.com) | [🌐 Portfolio](https://shaunalphonso.com)
#             """)
    
#     # Footer
#     st.markdown('<div class="footer">Built with ❤️ by <strong>Shaun Alphonso</strong> | Showcasing AI/ML Engineering & Digital Marketing Expertise<br>🚀 <em>This tool is part of my professional portfolio demonstrating production-ready AI applications</em></div>', unsafe_allow_html=True)

# if __name__ == "__main__":
#     main()
