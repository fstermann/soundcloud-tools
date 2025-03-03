import streamlit as st


def main():
    st.set_page_config(
        page_title="SoundCloud Tools",
        page_icon=":material/cloud:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    pg = st.navigation(
        [
            st.Page("tools/meta_editor.py"),
        ]
    )
    pg.run()


if __name__ == "__main__":
    main()
