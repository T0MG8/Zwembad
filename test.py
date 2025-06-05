import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

gebruikers = {
    "Benthe": "q",
    "Sara": "q"
}

# GSheets verbindingen


# Inlogstatus bijhouden
if 'ingelogd' not in st.session_state:
    st.session_state.ingelogd = False
if 'gebruiker' not in st.session_state:
    st.session_state.gebruiker = ""

# Als ingelogd, toon tabs
if st.session_state.ingelogd:
    tab1, tab2, tab3 = st.tabs(['Wat kunnen', 'Aanwezigheid', 'test'])

    with tab1:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data_n1 = conn.read(worksheet="niveau1", ttl=0)
        data_n2 = conn.read(worksheet="niveau2", ttl=0)
        data_n3 = conn.read(worksheet="niveau3", ttl=0)
        data_ad = conn.read(worksheet="adiploma", ttl=0)
        data_bd = conn.read(worksheet="bdiploma", ttl=0)
        data_cd = conn.read(worksheet="cdiploma", ttl=0)
        # ── 2. Structuur uit de sheet halen ──────────────────────────────────────────
        rijlabel_kol  = data_n1.columns[0]             # eerste kolom bevat de namen
        kinderen      = data_n1[rijlabel_kol].tolist() # ['Peter', 'Sjaqelien', …]
        kolom_n1      = data_n1.columns[1:].tolist()   # opdrachten

        # Alle symbolen die al in de sheet voorkomen (plus lege waarde) worden opties
        symbool_set   = (
            data_n1.drop(columns=[rijlabel_kol])
            .stack()                # alle cell-waarden onder elkaar
            .dropna()
            .unique()
            .tolist()
        )
        # Sorteer in de volgorde die je gewend bent
        symbool_volgorde = ['', '➖', '➕', '✳️']
        kleuren_opties   = symbool_volgorde

        # ── 3. UI bouwen ─────────────────────────────────────────────────────────────
        with st.container():          # hele tabel in één container
            # header
            kol = st.columns(len(kolom_n1) + 1)
            kol[0].markdown(" ")      # lege cel links-boven
            for i, opdracht in enumerate(kolom_n1):
                kol[i + 1].markdown(f"<div class='tabel-box header'>{opdracht}</div>",
                                    unsafe_allow_html=True)

            # rijen
            for r, kind in enumerate(kinderen):
                kol = st.columns([1.3] + [1]*len(kolom_n1))
                kol[0].markdown(f"<div class='tabel-box rowlabel'>{kind}</div>",
                                unsafe_allow_html=True)

                for c, opdracht in enumerate(kolom_n1):
                    default = data_n1.loc[r, opdracht]
                    try:
                        idx = kleuren_opties.index(default)
                    except ValueError:
                        idx = 0                  

                    with kol[c + 1]:
                        st.selectbox(
                            label="",
                            options=kleuren_opties,
                            index=idx,
                            key=f"dropdown_{r}_{c}",
                            label_visibility="collapsed"
                        )
        if st.button("💾 Opslaan wijzigingen"):
            nieuw_data = data_n1.copy()

            for r, kind in enumerate(kinderen):
                for c, opdracht in enumerate(kolom_n1):
                    key = f"dropdown_{r}_{c}"
                    waarde = st.session_state.get(key, "")
                    nieuw_data.at[r, opdracht] = waarde

            conn.update(worksheet="niveau1", data=nieuw_data)
            st.success("Gegevens zijn opgeslagen!")

        with tab2:
            vandaag = datetime.now().strftime("%d-%m-%Y")
            st.markdown(f"###  **{vandaag}**")
            aanwezig_dict = {}
            for naam in kinderen:
                col1, col2 = st.columns([3, 1])
                col1.markdown(f"**{naam}**")
                aanwezig_dict[naam] = "ja" if col2.checkbox("", key=naam) else "nee"

            # 4️⃣  opslaan
            if st.button("Opslaan"):
                # ▸ lees de hele sheet (ttl=0 = geen caching)
                df_sheet = conn.read(worksheet="Aanwezigheid", ttl=0).copy()

                # ▸ bepaal kolomnamen die echt in je sheet staan
                #    (pas zo nodig aan!)
                COL_WIE     = "Wie"        # of 'wie' / 'Naam' ...
                COL_DATUM   = "Datum"
                COL_STATUS  = "Aanwezig"

                # ▸ verzamel nieuwe rijen (voorkom dubbele invoer)
                nieuwe_rijen = []
                for naam, status in aanwezig_dict.items():
                    al_bestaat = (
                        (df_sheet[COL_WIE] == naam) &
                        (df_sheet[COL_DATUM] == vandaag)
                    ).any()

                    if not al_bestaat:          # alleen toevoegen als er nog niets is
                        nieuwe_rijen.append(
                            {COL_WIE: naam, COL_DATUM: vandaag, COL_STATUS: status}
                        )

                if nieuwe_rijen:
                    # ▸ plak nieuwe rijen onder bestaande data
                    df_nieuw = pd.concat(
                        [df_sheet, pd.DataFrame(nieuwe_rijen)],
                        ignore_index=True
                    )

                    # ▸ schrijf alles terug
                    conn.update(worksheet="Aanwezigheid", data=df_nieuw)
                    st.success(f"{len(nieuwe_rijen)} rijen opgeslagen!")
                else:
                    st.info("Alle namen waren al geregistreerd voor vandaag.")



    with tab3:
        st.write("")

# Loginformulier
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