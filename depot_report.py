if not st.session_state.user:
        st.title("DEPOT REPORT SYSTEM")
        st.subheader("Depot Agent Login")

        with st.form("login_form"):
            uid_input = st.text_input("Login ID")
            pwd_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("LOGIN")

        if submitted:
            uid = uid_input.strip().lower().replace(" ", "")
            pwd = pwd_input.strip()
            if uid in USERS and USERS[uid][0] == pwd:
                st.session_state.user = (uid, USERS[uid][1])
                st.rerun()
            else:
                st.error("Galat Login ID ya Password.")

        return
