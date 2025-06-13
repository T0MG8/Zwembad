import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Gebruikers en wachtwoorden
gebruikers = {
    "Benthe": "q",
    "Sara": "q",
    "Tom": "q"
}

# Maak verbinding met Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Inlogstatus bijhouden
if 'ingelogd' not in st.session_state:
    st.session_state.ingelogd = False
if 'gebruiker' not in st.session_state:
    st.session_state.gebruiker = ""

# Als ingelogd, toon tabs
if st.session_state.ingelogd:
    tabs = ['Wat kunnen', 'Aanwezigheid']
    if st.session_state.gebruiker in ["Tom", "Benthe"]:
        tabs.append('Instellingen')
    selected_tabs = st.tabs(tabs)

    with selected_tabs[0]:
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

        rijlabel_kol = data.columns[0]
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
                            key=f"{gekozen_sheet}_dropdown_{r}_{c}",
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

    with selected_tabs[1]:
        vandaag = datetime.now().strftime("%d-%m-%Y")
        st.markdown(f"###  **{vandaag}**")

        df_sheet = conn.read(worksheet="Aanwezigheid", ttl=0).copy()

        # Kolomnamen
        COL_WIE     = "Wie"
        COL_GROEP   = "Groep"
        COL_DATUM   = "Datum"
        COL_STATUS  = "Aanwezig"

        aanwezig_dict = {}

        for naam in kinderen:
            # Check of deze naam vandaag al geregistreerd is
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

                # Check of naam al een rij heeft vandaag
                bestaand_masker = (
                    (df_sheet[COL_WIE] == naam) &
                    (df_sheet[COL_DATUM] == vandaag)
                )

                if bestaand_masker.any():
                    # Update bestaande rij
                    df_sheet.loc[bestaand_masker, COL_STATUS] = status_nieuw
                else:
                    nieuwe_rijen.append({
                        COL_WIE: naam,
                        COL_GROEP: sheet_keuze,
                        COL_DATUM: vandaag,
                        COL_STATUS: status_nieuw
                    })

            # Voeg nieuwe rijen toe als die er zijn
            if nieuwe_rijen:
                df_sheet = pd.concat([df_sheet, pd.DataFrame(nieuwe_rijen)], ignore_index=True)

            # Update de sheet
            conn.update(worksheet="Aanwezigheid", data=df_sheet)
            st.success("Aanwezigheid opgeslagen of bijgewerkt!")


        st.markdown("---")
        st.subheader("📊 Aanwezigheidsoverzicht")

        # ▸ Laad aanwezigheidssheet
        df_overzicht = conn.read(worksheet="Aanwezigheid", ttl=0).copy()

        # ▸ Filter op alleen huidige groep (niveau)
        df_overzicht = df_overzicht[df_overzicht["Groep"] == sheet_keuze]

        # ▸ Pivoteren naar tabel: rijen = namen, kolommen = datums
        if not df_overzicht.empty:
            aanwezigheid_tabel = df_overzicht.pivot_table(
                index="Wie",
                columns="Datum",
                values="Aanwezig",
                aggfunc="first",  # Neem gewoon het eerste voorkomen als er meerdere rijen zijn
                fill_value=""
            )

            # Optioneel sorteren op naam of datum
            aanwezigheid_tabel = aanwezigheid_tabel.sort_index()
            aanwezigheid_tabel = aanwezigheid_tabel[sorted(aanwezigheid_tabel.columns, key=lambda d: datetime.strptime(d, "%d-%m-%Y"))]

            # ✅❌ vervangen i.p.v. 'ja' / 'nee'
            tabel_mooi = aanwezigheid_tabel.replace({
                "ja": "✅",
                "nee": "❌"
            })

            # Laat zien met styling
            st.dataframe(tabel_mooi, use_container_width=True)
        else:
            st.info(f"Nog geen aanwezigheidsdata voor '{sheet_keuze}'.")




    if st.session_state.gebruiker in ["Tom", "Benthe"]:
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
                    data = conn.read(worksheet=worksheet_naam, ttl=0)

                    if 'Naam' not in data.columns:
                        data['Naam'] = ""

                    nieuwe_rij = {col: "" for col in data.columns}
                    nieuwe_rij['Naam'] = naam_toevoegen

                    data = pd.concat([data, pd.DataFrame([nieuwe_rij])], ignore_index=True)
                    conn.update(worksheet=worksheet_naam, data=data)

                    st.success(f"Naam '{naam_toevoegen}' toegevoegd aan worksheet '{gekozen_sheet}'.")

            st.markdown("---")
            st.subheader("Verplaats een naam naar een ander niveau")

            # Stap 1: Kies huidig niveau
            niveau_bron = st.selectbox(
                "Van welk niveau wil je een naam verplaatsen?",
                options=list(sheet_mapping.keys()),
                key="verplaats_van"
            )
            sheet_bron = sheet_mapping[niveau_bron]

            # Stap 2: Kies een naam uit de bron-sheet
            data_bron = conn.read(worksheet=sheet_bron, ttl=0)
            namen_in_bron = data_bron['Naam'].dropna().tolist() if 'Naam' in data_bron.columns else []

            naam_te_verplaatsen = st.selectbox(
                "Welke naam wil je verplaatsen?",
                options=namen_in_bron,
                key="verplaats_naam"
            )

            # Stap 3: Kies doel-niveau (mag niet hetzelfde zijn)
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
                    # Verwijder naam uit bron
                    data_bron = data_bron[data_bron['Naam'] != naam_te_verplaatsen]
                    conn.update(worksheet=sheet_bron, data=data_bron)

                    # Voeg toe aan doel
                    data_doel = conn.read(worksheet=sheet_doel, ttl=0)
                    if 'Naam' not in data_doel.columns:
                        data_doel['Naam'] = ""
                    nieuwe_rij = {col: "" for col in data_doel.columns}
                    nieuwe_rij['Naam'] = naam_te_verplaatsen
                    data_doel = pd.concat([data_doel, pd.DataFrame([nieuwe_rij])], ignore_index=True)
                    conn.update(worksheet=sheet_doel, data=data_doel)

                    st.success(f"Naam '{naam_te_verplaatsen}' is verplaatst van '{niveau_bron}' naar '{niveau_doel}'.")
                
            st.markdown("---")
            st.subheader("Verwijder een persoon")

            # Stap 1: Kies het niveau
            verwijder_niveau = st.selectbox(
                "Kies een niveau waaruit je een naam wilt verwijderen:",
                options=list(sheet_mapping.keys()),
                key="verwijder_niveau"
            )
            verwijder_sheet = sheet_mapping[verwijder_niveau]

            # Stap 2: Lees namen uit dat sheet
            data_verwijder = conn.read(worksheet=verwijder_sheet, ttl=0)
            namen_om_te_verwijderen = data_verwijder['Naam'].dropna().tolist() if 'Naam' in data_verwijder.columns else []

            # Stap 3: Kies de naam om te verwijderen
            naam_verwijderen = st.selectbox(
                "Welke naam wil je verwijderen?",
                options=namen_om_te_verwijderen,
                key="verwijder_naam"
            )

            # Verwijderknop
            if st.button("🗑️ Verwijder naam"):
                if naam_verwijderen.strip() == "":
                    st.error("Selecteer een naam om te verwijderen.")
                else:
                    data_verwijder = data_verwijder[data_verwijder['Naam'] != naam_verwijderen]
                    conn.update(worksheet=verwijder_sheet, data=data_verwijder)
                    st.success(f"Naam '{naam_verwijderen}' is verwijderd uit niveau '{verwijder_niveau}'.")


# ---------------------------------------------------------------------------------------------------------------------------------------

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