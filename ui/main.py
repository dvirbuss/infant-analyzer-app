import datetime
import streamlit as st
from pathlib import Path

# Internal imports
import config
from ui.styles import base_css, generate_button_css
from ui.components.pose_card import render_pose_card, PoseSpec
from ui.utils_upload import save_video_bytes
from core.pipeline import run as run_pipeline


def render_app():
    # --- Setup ---
    st.set_page_config(page_title="Infant Motor Development Analyzer", layout="wide")
    st.markdown(base_css(), unsafe_allow_html=True)

    st.markdown("<div class='app-title'>Infant Motor Development Analyzer</div>", unsafe_allow_html=True)
    st.markdown("<div class='app-subtitle'>Choose an infant birthday and load the evaluation videos.</div>", unsafe_allow_html=True)

    # --- 1. Birthday (Centered) ---
    _, center_date, _ = st.columns([4, 3, 4])
    with center_date:
        st.markdown("<h4 style='text-align:center; color:#2c3e50; font-weight:600;'>Select Infant Birthday</h4>", unsafe_allow_html=True)
        birth_date = st.date_input(
            "Infant birthday",
            value=datetime.date.today() - datetime.timedelta(days=60),
            format="DD/MM/YYYY",
            label_visibility="collapsed"
        )

    # --- 2. Render Cards ---
    poses = [
        PoseSpec(key="prone", title="Prone", icon_path=config.PRONE_ICON),
        PoseSpec(key="supine", title="Supine", icon_path=config.SUPINE_ICON),
        PoseSpec(key="sitting", title="Sitting", icon_path=config.SITTING_ICON),
    ]

    st.markdown("<h4 style='text-align:center;'>Load Infant Videos:</h4>", unsafe_allow_html=True)
    cols = st.columns(3, gap="large")

    for i, spec in enumerate(poses):
        with cols[i]:
            # Safety check: Prevent crash if icon is missing
            if not spec.icon_path.exists():
                st.warning(f"File not found: {spec.icon_path.name}")

            render_pose_card(
                spec=spec,
                save_fn=save_video_bytes,
                subdir_name=f"infant_{birth_date.strftime('%Y%m%d')}"
            )

    # --- 3. Generate Button (Centered & Green) ---
    # Check session state ONLY after all cards have been rendered
    confirmed_keys = [k for k in ["prone", "supine", "sitting"] if st.session_state.get(f"{k}__confirmed")]
    any_confirmed = len(confirmed_keys) > 0

    # Centered button column
    _, btn_col, _ = st.columns([5, 2, 5])

    with btn_col:
        # Use your existing CSS function
        st.markdown(generate_button_css(any_confirmed), unsafe_allow_html=True)

        if st.button("GENERATE", type="primary", disabled=not any_confirmed):
            progress_text = st.empty()
            progress_text.info("Running unified analysis for selected poses...")

            try:
                # Prepare dictionary of paths
                video_paths = {}
                for pk in confirmed_keys:
                    video_paths[pk.capitalize()] = st.session_state.get(f"{pk}__saved_path")
                
                stamp = datetime.datetime.now().strftime('%d-%m-%y_%H-%M')
                out_dir = config.VIDEOS_OUTPUT_DIR / f"Exam_{stamp}_streamlit"
                
                # Run unified pipeline
                from core.pipeline import process_full_exam
                result = process_full_exam(video_paths, birth_date, out_dir, caller="streamlit")
                
                progress_text.success(f"Analysis complete! Infant Score: {result['aims_score']}")
                st.balloons()
                
                # Display the combined reports
                reports = result.get("reports", {})
                col1, col2 = st.columns(2)
                with col1:
                    if "expert_plot" in reports and Path(reports["expert_plot"]).exists():
                        st.image(reports["expert_plot"], caption="Expert Report", use_column_width=True)
                with col2:
                    if "parent_plot" in reports and Path(reports["parent_plot"]).exists():
                        st.image(reports["parent_plot"], caption="Parent Report", use_column_width=True)
                        
            except Exception as e:
                import traceback
                st.error(f"Error during analysis: {e}")
                st.code(traceback.format_exc())
    # --- 4. DEBUG SECTION (See where it's looking) ---
    with st.expander("🛠️ Debug Path Info"):
        st.write(f"**BASE_DIR:** `{config.BASE_DIR}`")
        st.write(f"**ASSETS_DIR:** `{config.ASSETS_DIR}`")
        for p in poses:
            exists = "✅ Found" if p.icon_path.exists() else "❌ NOT FOUND"
            st.write(f"**{p.title} Icon Path:** `{p.icon_path}` | {exists}")