import streamlit as st

from soundcloud_tools.client import Client


class StreamlitClient(Client):
    @st.cache_data
    def _make_request(self, *arg, **kwargs):
        return self.make_request(*arg, **kwargs)


@st.cache_resource
def get_client():
    return StreamlitClient()
