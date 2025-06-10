import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

gebruikers = {
    "Benthe": "q",
    "Sara": "q"
}

conn = st.connection("gsheets", type=GSheetsConnection)

# Inlogstatus bijhouden
if 'ingelogd' not in st.session_state:
    st.session_state.ingelogd = False
if 'gebruiker' not in st.session_state:
    st.session_state.gebruiker = ""

# Als ingelogd, toon tabs
if st.session_state.ingelogd:
    tab1, tab2, tab3 = st.tabs(['Wat kunnen', 'Aanwezigheid', 'Instellingen'])
    
    with tab1:
        # Dropdown om een niveau of diploma te kiezen
        sheet_keuze = st.selectbox(
            "Selecteer een niveau of diploma",
            options=["Niveau 1", "Niveau 2", "Niveau 3", "A Diploma", "B Diploma", "C Diploma"]
        )

        st.markdown("---")

        # Mapping van dropdownkeuze naar werkelijke worksheetnamen
        sheet_mapping = {
            "Niveau 1": "niveau1",
            "Niveau 2": "niveau2",
            "Niveau 3": "niveau3",
            "A Diploma": "adiploma",
            "B Diploma": "bdiploma",
            "C Diploma": "cdiploma"
        }

        gekozen_sheet = sheet_mapping[sheet_keuze]
        data = conn.read(worksheet=gekozen_sheet, ttl=5).dropna(how="all")

        # ── Structuur uit de sheet halen ───────────────────────────────
        rijlabel_kol = data.columns[0]             # eerste kolom bevat de namen
        kinderen = data[rijlabel_kol].tolist()
        kolom_opdrachten = data.columns[1:].tolist()

        symbool_set = (
            data.drop(columns=[rijlabel_kol])
            .stack()
            .dropna()
            .unique()
            .tolist()
        )

        symbool_volgorde = ['', '➖', '➕', '✳️']
        kleuren_opties = symbool_volgorde

        # ── UI bouwen ───────────────────────────────────────────────────
        with st.container():
            kol = st.columns(len(kolom_opdrachten) + 1)
            kol[0].markdown(" ")  # lege header
            for i, opdracht in enumerate(kolom_opdrachten):
                kol[i + 1].markdown(f"<div class='tabel-box header'>{opdracht}</div>",
                                    unsafe_allow_html=True)

            for r, kind in enumerate(kinderen):
                kol = st.columns([1.3] + [1]*len(kolom_opdrachten))
                kol[0].markdown(f"<div class='tabel-box rowlabel'>{kind}</div>",
                                unsafe_allow_html=True)

                for c, opdracht in enumerate(kolom_opdrachten):
                    default = data.loc[r, opdracht]
                    try:
                        idx = kleuren_opties.index(default)
                    except ValueError:
                        idx = 0

                    with kol[c + 1]:
                        st.selectbox(
                            label="",
                            options=kleuren_opties,
                            index=idx,
                            key=f"{gekozen_sheet}_dropdown_{r}_{c}",  # uniek per sheet
                            label_visibility="collapsed"
                        )

        st.markdown("---")
        if st.button("💾 Opslaan wijzigingen"):
            nieuw_data = data.copy()

            for r, kind in enumerate(kinderen):
                for c, opdracht in enumerate(kolom_opdrachten):
                    key = f"{gekozen_sheet}_dropdown_{r}_{c}"
                    waarde = st.session_state.get(key, "")
                    nieuw_data.at[r, opdracht] = waarde

            conn.update(worksheet=gekozen_sheet, data=nieuw_data)
            st.success(f"Gegevens voor {sheet_keuze} zijn opgeslagen!")


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