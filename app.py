import streamlit as st
import os
import time
import pandas as pd
import json
import requests
from bs4 import BeautifulSoup
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

# ---------------------
# WebsiteAnalyzer class (unchanged)
# ---------------------
class WebsiteAnalyzer:
    """Main class for website analysis functionality."""
    
    def __init__(self):
        self.setup_openai()
    
    def setup_openai(self):
        """Setup OpenAI client with API key."""
        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("🚨 OpenAI API key not found! Please add it to your Streamlit secrets.")
            st.stop()
        self.openai_client = OpenAI(api_key=api_key)
    
    @st.cache_data(ttl=3600)  # Cache results for 1 hour
    def scrape_website(_self, url: str) -> str:
        """Extract visible text content from a website using requests + BeautifulSoup."""
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/115.0.0.0 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove scripts, styles, and non-visible elements
            for element in soup(["script", "style", "noscript"]):
                element.extract()

            text = soup.get_text(separator=" ", strip=True)

            return text if text else "Error: No text content found."
        
        except requests.exceptions.RequestException as e:
            return f"Error extracting content: {str(e)}"
    
    def analyze_content(self, content: str, url: str) -> dict:
        """Analyze website content using AI."""
        
        if not content or "Error" in content:
            return {"error": content}
        
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

# ---------------------
# Main UI - layout changed so primary controls and analysis are centered
# ---------------------
def main():
    # Header area (we will center the big title visually via the middle column)
    left_col, center_col, right_col = st.columns([1, 2, 1])
    with center_col:
        st.markdown('<h1 class="main-header">🚀 AI Marketing Analyzer</h1>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Professional website analysis and marketing recommendations powered by AI</p>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;"><span class="demo-badge">💼 PORTFOLIO DEMO</span></div>', unsafe_allow_html=True)

    # Sidebar (left toolbar) - move "Built by" and capabilities here
    with st.sidebar:
        st.header("💡 Built by")
        st.markdown("**Shaun Alphonso**")
        st.info("""
Welcome to my first vibe-coded app! As a marketer of the future, I'd love to hear about your experience using this app.

[📧 Contact](mailto:shaun@georgian.io) | [🌐 LinkedIn](https://www.linkedin.com/in/shaunalphonso/)
        """)
        st.markdown("---")
        st.markdown("### This tool demonstrates advanced capabilities in:")
        for feature in [
            "🤖 AI Integration: OpenAI GPT-4",
            "🕷️ Web Scraping: BeautifulSoup",
            "📊 Data Processing: Pandas",
            "🚀 Web Development: Streamlit"
        ]:
            st.markdown(f"- {feature}")
        st.markdown("---")
        st.caption("Tip: enter a URL in the center panel and click Analyze.")

    # Initialize analyzer in session state if not present
    if 'analyzer' not in st.session_state:
        with st.spinner("🔧 Initializing AI marketing analyzer..."):
            st.session_state.analyzer = WebsiteAnalyzer()

    # Center column: URL input, features, and examples (examples appear below features)
    col_left, col_center, col_right = st.columns([0.5, 1, 0.5])
    with col_center:
        url = st.text_input(
            "Enter Website URL:",
            placeholder="https://example.com",
            hel


# import streamlit as st
# import os
# import time
# import pandas as pd
# import json
# import requests
# from bs4 import BeautifulSoup
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
#         self.setup_openai()
    
#     def setup_openai(self):
#         """Setup OpenAI client with API key."""
#         api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
#         if not api_key:
#             st.error("🚨 OpenAI API key not found! Please add it to your Streamlit secrets.")
#             st.stop()
#         self.openai_client = OpenAI(api_key=api_key)
    
#     @st.cache_data(ttl=3600)  # Cache results for 1 hour
#     def scrape_website(_self, url: str) -> str:
#         """Extract visible text content from a website using requests + BeautifulSoup."""
#         try:
#             headers = {
#                 "User-Agent": (
#                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                     "AppleWebKit/537.36 (KHTML, like Gecko) "
#                     "Chrome/115.0.0.0 Safari/537.36"
#                 )
#             }
#             response = requests.get(url, headers=headers, timeout=15)
#             response.raise_for_status()

#             soup = BeautifulSoup(response.text, "html.parser")

#             # Remove scripts, styles, and non-visible elements
#             for element in soup(["script", "style", "noscript"]):
#                 element.extract()

#             text = soup.get_text(separator=" ", strip=True)

#             return text if text else "Error: No text content found."
        
#         except requests.exceptions.RequestException as e:
#             return f"Error extracting content: {str(e)}"
    
#     def analyze_content(self, content: str, url: str) -> dict:
#         """Analyze website content using AI."""
        
#         if not content or "Error" in content:
#             return {"error": content}
        
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
    
#     st.markdown('<h1 class="main-header">🚀 AI Marketing Analyzer</h1>', unsafe_allow_html=True)
#     st.markdown('<p class="sub-header">Professional website analysis and marketing recommendations powered by AI</p>', unsafe_allow_html=True)
    
#     col1, col2, col3 = st.columns([1, 2, 1])
#     with col2:
#         st.markdown('<div style="text-align: center;"><span class="demo-badge">💼 PORTFOLIO DEMO</span></div>', unsafe_allow_html=True)
    
#     if 'analyzer' not in st.session_state:
#         with st.spinner("🔧 Initializing AI marketing analyzer..."):
#             st.session_state.analyzer = WebsiteAnalyzer()
    
#     with st.sidebar:
#         st.header("🎯 Website Analysis")
#         url = st.text_input(
#             "Enter Website URL:",
#             placeholder="https://example.com",
#             help="Enter any website URL for comprehensive marketing analysis"
#         )
#         analyze_button = st.button("🔍 Analyze Website", type="primary", use_container_width=True)
        
#         st.markdown("---")
#         st.markdown("### 📋 Analysis Features:")
#         for feature in [
#             "🔍 SEO keyword identification",
#             "📊 Marketing strategy analysis", 
#             "👥 Target audience insights",
#             "💡 Value proposition review",
#             "🎯 Call-to-action audit",
#             "📝 Content theme analysis",
#             "🚀 Growth recommendations"
#         ]:
#             st.markdown(f"- {feature}")
        
#         st.markdown("---")
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
    
#     if hasattr(st.session_state, 'example_url'):
#         url = st.session_state.example_url
#         delattr(st.session_state, 'example_url')
#         analyze_button = True
    
#     if analyze_button and url:
#         if not url.startswith(('http://', 'https://')):
#             url = 'https://' + url
        
#         progress_container = st.container()
#         with progress_container:
#             st.markdown("### 🔄 Analysis in Progress")
#             progress_bar = st.progress(0)
#             status_text = st.empty()
            
#             try:
#                 status_text.success("🕷️ Step 1: Extracting website content...")
#                 progress_bar.progress(25)
#                 content = st.session_state.analyzer.scrape_website(url)
#                 time.sleep(1)
                
#                 status_text.success("🧠 Step 2: AI analysis in progress...")
#                 progress_bar.progress(50)
#                 analysis_results = st.session_state.analyzer.analyze_content(content, url)
#                 if "error" in analysis_results:
#                     st.error(f"❌ Analysis failed: {analysis_results['error']}")
#                     return
#                 time.sleep(1)
                
#                 status_text.success("💡 Step 3: Generating marketing recommendations...")
#                 progress_bar.progress(75)
#                 recommendations = st.session_state.analyzer.generate_recommendations(analysis_results)
                
#                 status_text.success("✅ Step 4: Analysis complete!")
#                 progress_bar.progress(100)
#                 time.sleep(1)
                
#                 progress_bar.empty()
#                 status_text.empty()
                
#                 st.markdown("---")
#                 st.markdown("## 📊 Analysis Results")
                
#                 col1, col2, col3 = st.columns(3)
#                 with col1:
#                     keywords = analysis_results.get("SEO Keywords", "").split(",")
#                     st.markdown(f'<div class="metric-container"><h3>🔍 SEO Keywords</h3><h2>{len([k for k in keywords if k.strip()])}</h2><p>Keywords identified</p></div>', unsafe_allow_html=True)
#                 with col2:
#                     ctas = analysis_results.get("Call-to-Actions", "").split(",")
#                     st.markdown(f'<div class="metric-container"><h3>🎯 Call-to-Actions</h3><h2>{len([c for c in ctas if c.strip()])}</h2><p>CTAs found</p></div>', unsafe_allow_html=True)
#                 with col3:
#                     st.markdown(f'<div class="metric-container"><h3>📄 Content Volume</h3><h2>{analysis_results.get("Content_Length", 0):,}</h2><p>Characters analyzed</p></div>', unsafe_allow_html=True)
                
#                 st.markdown("### 📈 Detailed Analysis")
#                 for key, value in analysis_results.items():
#                     if key not in ["URL", "Content_Length", "error"] and not value.startswith("Analysis error"):
#                         st.markdown(f"**{key}:**")
#                         st.info(value)
                
#                 st.markdown("### 🚀 AI Marketing Recommendations")
#                 rec_cols = st.columns(2)
#                 col_index = 0
#                 for category, recommendations_text in recommendations.items():
#                     with rec_cols[col_index % 2]:
#                         st.markdown(f"#### {category}")
#                         st.markdown(f'<div class="recommendation-card">{recommendations_text}</div>', unsafe_allow_html=True)
#                     col_index += 1
                
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
#                     df = pd.DataFrame([analysis_results])
#                     st.download_button(
#                         "📈 Download CSV Data",
#                         data=df.to_csv(index=False),
#                         file_name=f"analysis_data_{time.strftime('%Y%m%d_%H%M%S')}.csv",
#                         mime="text/csv",
#                         use_container_width=True
#                     )
#                 st.markdown('<div class="success-message">🎉 <strong>Analysis Complete!</strong> Your comprehensive marketing report is ready. Use the recommendations above to optimize your website\'s performance.</div>', unsafe_allow_html=True)
            
#             except Exception as e:
#                 progress_bar.empty()
#                 status_text.empty()
#                 st.markdown(f'<div class="error-message">❌ <strong>Analysis Failed:</strong> {str(e)}</div>', unsafe_allow_html=True)
    
#     elif analyze_button and not url:
#         st.warning("⚠️ Please enter a website URL to begin analysis.")
#     else:
#         st.markdown("### 👋 Welcome to the AI Marketing Analyzer")
#         col1, col2 = st.columns([3, 2])
#         with col1:
#             st.markdown("""
#             Want to understand how your website strategy is working?
            
#             This tool demonstrates advanced capabilities in:
            
#             - **🤖 AI Integration**: OpenAI GPT-4 for intelligent content analysis
#             - **🕷️ Web Scraping**: Automated data extraction using BeautifulSoup
#             - **📊 Data Processing**: Real-time analysis and insights generation
#             - **💼 Marketing Strategy**: Professional-grade recommendations
#             - **🚀 Web Development**: Production-ready Streamlit application
            
#             Enter any website URL in the sidebar to begin your analysis!
#             """)
#         with col2:
#             st.info("""
#             **💡 Built by Shaun Alphonso**
            
#             Welcome to my first vibe-coded app! As a marketer of the future, I'd love to hear about your experience using this app.
            
#             [📧 Contact](mailto:shaun@georgian.io) | [🌐 LinkedIn](https://www.linkedin.com/in/shaunalphonso/)
#             """)
    
#     st.markdown('<div class="footer">Built with ❤️ by <strong>Shaun Alphonso</strong> | Experimenting with AI/ML Engineering & Digital Marketing<br>🚀 <em>This tool is part of my professional portfolio demonstrating production-ready AI applications</em></div>', unsafe_allow_html=True)

# if __name__ == "__main__":
#     main()
