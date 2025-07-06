import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Zwembad De Breek",
    layout="wide"
)

# Gebruikers en wachtwoorden
gebruikers = {
    "Benthe": "q",
    "Zwemles": "Breek"
}

# Maak verbinding met Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Cache functie om data op te halen, zonder dat Streamlit de 'conn' hoeft te hashen
@st.cache_data(ttl=30)
def get_data(_conn, worksheet):
    return _conn.read(worksheet=worksheet).dropna(how="all")

# Inlogstatus bijhouden
if 'ingelogd' not in st.session_state:
    st.session_state.ingelogd = False
if 'gebruiker' not in st.session_state:
    st.session_state.gebruiker = ""

if st.session_state.ingelogd:
    tabs = ['Wat kunnen', 'Aanwezigheid']
    if st.session_state.gebruiker in ["Benthe"]:
        tabs.append('Instellingen')
    selected_tabs = st.tabs(tabs)

    with selected_tabs[0]:
        sheet_keuze = st.selectbox(
            "Selecteer een niveau of diploma",
            options=["Niveau 1", "Niveau 2", "Niveau 3", "A Diploma", "B Diploma", "C Diploma"]
        )

        st.markdown("---")

        sheet_mapping = {
            "Niveau 1": "niveau1",
            "Niveau 2": "niveau2",
            "Niveau 3": "niveau3",
            "A Diploma": "adiploma",
            "B Diploma": "bdiploma",
            "C Diploma": "cdiploma"
        }

        gekozen_sheet = sheet_mapping[sheet_keuze]
        try:
            data = get_data(conn, gekozen_sheet)
        except Exception as e:
            st.error(f"❌ Fout bij het laden van gegevens uit het sheet: {str(e)}")
            st.stop()

        rijlabel_kol = data.columns[0]
        kinderen = data[rijlabel_kol].tolist()
        kolom_opdrachten = data.columns[1:].tolist()

        symbool_volgorde = ['', '➖', '➕', '✳️']

        bewerkbare_data = data.copy()
        bewerkbare_data.reset_index(drop=True, inplace=True)

        try:
            from streamlit.column_config import SelectboxColumn

            kolom_config = {
                kolom: SelectboxColumn(
                    options=symbool_volgorde,
                    required=False
                ) for kolom in kolom_opdrachten
            }

            st.markdown("""
                <style>
                thead tr th div {
                    white-space: normal !important;
                    word-wrap: break-word !important;
                    text-align: center !important;
                }
                .stDataFrameContainer {
                    max-height: none !important;
                    height: auto !important;
                    overflow: visible !important;
                }
                </style>
            """, unsafe_allow_html=True)

            nieuwe_data = st.data_editor(
                bewerkbare_data,
                column_config=kolom_config,
                use_container_width=True,
                hide_index=True
            )
        except Exception:
            nieuwe_data = st.data_editor(
                bewerkbare_data,
                use_container_width=True,
                hide_index=True
            )

        st.markdown("---")

        if st.button("💾 Opslaan wijzigingen"):
            nieuwe_data[rijlabel_kol] = data[rijlabel_kol]
            nieuwe_data = nieuwe_data[[rijlabel_kol] + kolom_opdrachten]
            conn.update(worksheet=gekozen_sheet, data=nieuwe_data)
            st.success(f"Gegevens voor {sheet_keuze} zijn opgeslagen!")

    with selected_tabs[1]:
        vandaag = datetime.now().strftime("%d-%m-%Y")
        st.markdown(f"###  **{vandaag}**")

        # Lees aanwezigheidsdata opnieuw direct (ttl=0 kan hier omdat we willen meest recente data)
        try:
            df_sheet = conn.read(worksheet="Aanwezigheid", ttl=0).copy()
        except Exception as e:
            st.error(f"❌ Fout bij het laden van aanwezigheidsgegevens: {str(e)}")
            st.stop()

        # Kolomnamen
        COL_WIE     = "Wie"
        COL_GROEP   = "Groep"
        COL_DATUM   = "Datum"
        COL_STATUS  = "Aanwezig"

        aanwezig_dict = {}

        for naam in kinderen:
            rij = df_sheet[
                (df_sheet[COL_WIE] == naam) &
                (df_sheet[COL_DATUM] == vandaag)
            ]

            status = rij[COL_STATUS].values[0] if not rij.empty else "nee"

            col1, col2 = st.columns([3, 1])
            col1.markdown(f"**{naam}**")
            aanwezig_dict[naam] = col2.checkbox("", value=(status == "ja"), key=f"checkbox_{naam}")

        if st.button("Opslaan"):
            nieuwe_rijen = []
            for naam, status_checkbox in aanwezig_dict.items():
                status_nieuw = "ja" if status_checkbox else "nee"

                bestaand_masker = (
                    (df_sheet[COL_WIE] == naam) &
                    (df_sheet[COL_DATUM] == vandaag)
                )

                if bestaand_masker.any():
                    df_sheet.loc[bestaand_masker, COL_STATUS] = status_nieuw
                else:
                    nieuwe_rijen.append({
                        COL_WIE: naam,
                        COL_GROEP: sheet_keuze,
                        COL_DATUM: vandaag,
                        COL_STATUS: status_nieuw
                    })

            if nieuwe_rijen:
                df_sheet = pd.concat([df_sheet, pd.DataFrame(nieuwe_rijen)], ignore_index=True)

            conn.update(worksheet="Aanwezigheid", data=df_sheet)
            st.success("Aanwezigheid opgeslagen of bijgewerkt!")

        st.markdown("---")
        st.subheader("📊 Aanwezigheidsoverzicht")

        df_overzicht = conn.read(worksheet="Aanwezigheid", ttl=0).copy()

        df_overzicht = df_overzicht[df_overzicht["Groep"] == sheet_keuze]

        if not df_overzicht.empty:
            aanwezigheid_tabel = df_overzicht.pivot_table(
                index="Wie",
                columns="Datum",
                values="Aanwezig",
                aggfunc="first", 
                fill_value=""
            )
            aanwezigheid_tabel = aanwezigheid_tabel.sort_index()
            aanwezigheid_tabel = aanwezigheid_tabel[sorted(aanwezigheid_tabel.columns, key=lambda d: datetime.strptime(d, "%d-%m-%Y"))]

            tabel_mooi = aanwezigheid_tabel.replace({
                "ja": "✅",
                "nee": "❌"
            })

            st.dataframe(tabel_mooi, use_container_width=True)
        else:
            st.info(f"Nog geen aanwezigheidsdata voor '{sheet_keuze}'.")

    if st.session_state.gebruiker in ["Benthe"]:
        with selected_tabs[2]:
            st.title("Instellingen")
            st.markdown("---")
            st.subheader("Voeg een persoon toe")

            gekozen_sheet = st.selectbox("Kies een worksheet om naam toe te voegen:", options=list(sheet_mapping.keys()))
            worksheet_naam = sheet_mapping[gekozen_sheet]

            naam_toevoegen = st.text_input("Voer een naam in om toe te voegen:")

            if st.button("Voeg naam toe aan worksheet"):
                if naam_toevoegen.strip() == "":
                    st.error("Voer een geldige naam in.")
                else:
                    data = get_data(conn, worksheet_naam)

                    if 'Naam' not in data.columns:
                        data['Naam'] = ""

                    nieuwe_rij = {col: "" for col in data.columns}
                    nieuwe_rij['Naam'] = naam_toevoegen

                    data = pd.concat([data, pd.DataFrame([nieuwe_rij])], ignore_index=True)
                    conn.update(worksheet=worksheet_naam, data=data)

                    st.success(f"Naam '{naam_toevoegen}' toegevoegd aan worksheet '{gekozen_sheet}'.")

            st.markdown("---")
            st.subheader("Verplaats een naam naar een ander niveau")

            niveau_bron = st.selectbox(
                "Van welk niveau wil je een naam verplaatsen?",
                options=list(sheet_mapping.keys()),
                key="verplaats_van"
            )
            sheet_bron = sheet_mapping[niveau_bron]

            data_bron = get_data(conn, sheet_bron)
            namen_in_bron = data_bron['Naam'].dropna().tolist() if 'Naam' in data_bron.columns else []

            naam_te_verplaatsen = st.selectbox(
                "Welke naam wil je verplaatsen?",
                options=namen_in_bron,
                key="verplaats_naam"
            )

            niveau_doel_opties = [optie for optie in sheet_mapping.keys() if optie != niveau_bron]
            niveau_doel = st.selectbox(
                "Naar welk niveau wil je deze naam verplaatsen?",
                options=niveau_doel_opties,
                key="verplaats_naar"
            )
            sheet_doel = sheet_mapping[niveau_doel]

            if st.button("🔁 Verplaats naam"):
                if naam_te_verplaatsen.strip() == "":
                    st.error("Selecteer een naam om te verplaatsen.")
                else:
                    data_bron = data_bron[data_bron['Naam'] != naam_te_verplaatsen]
                    conn.update(worksheet=sheet_bron, data=data_bron)

                    data_doel = get_data(conn, sheet_doel)
                    if 'Naam' not in data_doel.columns:
                        data_doel['Naam'] = ""
                    nieuwe_rij = {col: "" for col in data_doel.columns}
                    nieuwe_rij['Naam'] = naam_te_verplaatsen
                    data_doel = pd.concat([data_doel, pd.DataFrame([nieuwe_rij])], ignore_index=True)
                    conn.update(worksheet=sheet_doel, data=data_doel)

                    st.success(f"Naam '{naam_te_verplaatsen}' is verplaatst van '{niveau_bron}' naar '{niveau_doel}'.")

            st.markdown("---")
            st.subheader("Verwijder een persoon")

            verwijder_niveau = st.selectbox(
                "Kies een niveau waaruit je een naam wilt verwijderen:",
                options=list(sheet_mapping.keys()),
                key="verwijder_niveau"
            )
            verwijder_sheet = sheet_mapping[verwijder_niveau]

            data_verwijder = get_data(conn, verwijder_sheet)
            namen_om_te_verwijderen = data_verwijder['Naam'].dropna().tolist() if 'Naam' in data_verwijder.columns else []

            naam_verwijderen = st.selectbox(
                "Welke naam wil je verwijderen?",
                options=namen_om_te_verwijderen,
                key="verwijder_naam"
            )

            if st.button("🗑️ Verwijder naam"):
                if naam_verwijderen.strip() == "":
                    st.error("Selecteer een naam om te verwijderen.")
                else:
                    data_verwijder = data_verwijder[data_verwijder['Naam'] != naam_verwijderen]
                    conn.update(worksheet=verwijder_sheet, data=data_verwijder)
                    st.success(f"Naam '{naam_verwijderen}' is verwijderd uit niveau '{verwijder_niveau}'.")

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
                st.experimental_rerun()
            else:
                st.error("Gebruikersnaam of wachtwoord is fout")
