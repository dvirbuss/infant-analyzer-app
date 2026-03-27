def base_css() -> str:
    return """
    <style>
    /* Import modern Google font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    /* Gradient Title */
    .app-title { 
        text-align: center; 
        font-size: 48px; 
        font-weight: 800; 
        margin-top: 1.5rem; 
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }

    .app-subtitle { 
        text-align: center; 
        font-size: 20px; 
        color: #555; 
        margin-bottom: 2.5rem; 
        font-weight: 500;
    }

    /* Glassmorphism / Modern Card styling */
    .pose-card { 
        background: #ffffff; 
        border-radius: 16px; 
        padding: 1.5rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04), 0 1px 4px rgba(0, 0, 0, 0.02); 
        border: 1px solid rgba(220, 230, 245, 0.8); 
        text-align: center; 
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }

    /* Hover Lift Effect */
    .pose-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 12px 24px rgba(0, 50, 150, 0.08), 0 4px 8px rgba(0, 0, 0, 0.04);
        border-color: #a8c6fa;
    }

    .pose-title {
        font-size: 20px;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }

    .pose-card img { 
        height: 160px !important; 
        width: auto !important; 
        object-fit: contain; 
        margin-bottom: 1rem;
    }

    /* Improved Video Box */
    .video-box {
        width: 100%;
        height: 220px;
        border-radius: 12px;
        border: 1px solid #e1e8f0;
        background: #f8fafc;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
    }

    .video-box video {
        width: 100%;
        height: 100%;
        object-fit: contain;
    }

    /* Clean Uploader input styling overrides */
    div[data-testid="stFileUploader"] {
        padding: 0.5rem 0;
    }
    
    /* Center Date Input visually */
    div[data-testid="stDateInput"] {
        margin: 0 auto;
        padding: 1rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        border: 1px solid #eee;
    }
    </style>
    """

def generate_button_css(enabled: bool) -> str:
    if enabled:
        return """
        <style>
        @keyframes pulse-green {
            0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4); }
            70% { box-shadow: 0 0 0 15px rgba(76, 175, 80, 0); }
            100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }
        }
        
        button[kind="primary"] {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%) !important;
            color: white !important;
            border-radius: 30px !important;
            border: none !important;
            width: 280px !important;
            height: 70px !important;
            font-size: 28px !important;
            font-weight: 700 !important;
            letter-spacing: 1px !important;
            box-shadow: 0 8px 16px rgba(76, 175, 80, 0.25) !important;
            transition: all 0.2s ease !important;
            animation: pulse-green 2s infinite !important;
        }

        button[kind="primary"]:hover {
            transform: scale(1.03) !important;
            box-shadow: 0 10px 20px rgba(76, 175, 80, 0.35) !important;
            filter: brightness(1.05) !important;
        }
        </style>
        """
    return """
    <style>
    button[kind="primary"] {
        background: #e2e8f0 !important;
        color: #94a3b8 !important;
        border-radius: 30px !important;
        border: 2px dashed #cbd5e1 !important;
        width: 280px !important;
        height: 70px !important;
        font-size: 28px !important;
        font-weight: 700 !important;
        cursor: not-allowed !important;
        box-shadow: none !important;
    }
    </style>
    """
