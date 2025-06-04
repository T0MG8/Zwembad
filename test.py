import streamlit as st

gebruikers = {
    "Benthe": "q",
    "Sara": "q"
}

# Sessietoestand voor inloggen
if 'ingelogd' not in st.session_state:
    st.session_state.ingelogd = False
if 'gebruiker' not in st.session_state:
    st.session_state.gebruiker = ""

# Als ingelogd, toon de tabs en laad data
if st.session_state.ingelogd:
    tab1, tab2, tab3 = st.tabs(['Wat kunnen', 'Aanwezigheid', 'test'])
    with tab1:
    # Hoofdapp zichtbaar na inloggen
        kleuren_opties = ['rood', 'oranje', 'geel', 'groen']
        kinderen = ["Peter", "Sjaqelien", "Gerard", "Geert", "Sjaak"]
        kolom_labels = ["Drijven", "Opduiken", "Rug", "Buik"]

        st.markdown("""
            <style>
            .tabel-box {
                padding: 5px;
                margin: 1px;
                text-align: center;
            }
            .header {
                color: black;
                font-weight: bold;
            }
            .rowlabel {
                color: black;
                font-weight: bold;
                text-align: left;
            }
            </style>
        """, unsafe_allow_html=True)

        kol = st.columns(len(kolom_labels) + 1)
        kol[0].markdown(f"<div class='tabel-box'></div>", unsafe_allow_html=True)
        for i in range(len(kolom_labels)):
            kol[i + 1].markdown(f"<div class='tabel-box header'>{kolom_labels[i]}</div>", unsafe_allow_html=True)

        for r in range(len(kinderen)):
            kol = st.columns(len(kolom_labels) + 1)
            kol[0].markdown(f"<div class='tabel-box rowlabel'>{kinderen[r]}</div>", unsafe_allow_html=True)
            for c in range(len(kolom_labels)):
                with kol[c + 1]:
                    st.selectbox(
                        label="",
                        options=kleuren_opties,
                        key=f"dropdown_{r}_{c}",
                        label_visibility="collapsed"
                    )
    with tab2:
        st.write("joehoe")
        for label in kinderen:
            cols = st.columns([3, 1])
            cols[0].markdown(f"**{label}**")
            cols[1].checkbox("", key=label)

    
    with tab3:
        st.write("joehoe")

#-------------------------------------------------------------------------------------------------------------------------------

#-------------------------------------------------------------------------------------------------------------------------------

# Login formulier tonen als nog niet ingelogd
if not st.session_state.ingelogd:
    st.title("Inloggen vereist")
    with st.form("login_form"):
        gebruikersnaam = st.text_input("Gebruikersnaam")
        wachtwoord = st.text_input("Wachtwoord", type="password")
        submitted = st.form_submit_button("Inloggen")
        if submitted:
            if gebruikersnaam in gebruikers and wachtwoord == gebruikers[gebruikersnaam]:
                st.session_state.ingelogd = True
                st.session_state.gebruiker = gebruikersnaam
            else:
                st.error("Gebruikersnaam of wachtwoord is fout")