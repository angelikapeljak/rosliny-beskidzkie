import glob
import os
import random
import pandas as pd
import streamlit as st

st.title("🌱 Rozpoznaj Beskidzkie Rośliny")


# 1. Load data (cached for performance)
@st.cache_data
def load_data():
    df = pd.read_csv("plants.csv")
    # Ensure column names match expectations (rename 'flower' to 'name' if necessary)
    if "flower" in df.columns and "name" not in df.columns:
        df = df.rename(columns={"flower": "name"})
    return df

try:
    df = load_data()
    total_plants = len(df)
except Exception as e:
    st.error(f"Błąd podczas ładowania pliku CSV: {e}")
    st.stop()

# Display total number of plants in the database
st.sidebar.write(f"Liczba roślin w bazie: **{total_plants}**")

# 2. Initialize session state variables
if "seen_plants" not in st.session_state:
    st.session_state.seen_plants = []
    st.session_state.score = 0
    st.session_state.current_plant = None
    st.session_state.options = None
    st.session_state.answered = False


# Helper function to find all images matching id XX.* or XX_*.*
def get_plant_images(plant_id):
    image_extensions = ("jpg", "jpeg", "JPG", "JPEG", "png", "PNG")
    found_images = []

    for ext in image_extensions:
        pattern_exact = os.path.join("images", f"{plant_id}.{ext}")
        pattern_prefix = os.path.join("images", f"{plant_id}_*.{ext}")

        found_images.extend(glob.glob(pattern_exact))
        found_images.extend(glob.glob(pattern_prefix))

    # Remove duplicates and sort for consistency
    return sorted(list(set(found_images)))


# Helper function to load a new unshown question
def get_next_question():
    unseen_df = df[~df.index.isin(st.session_state.seen_plants)]

    if len(unseen_df) == 0:
        st.session_state.current_plant = None
        return

    plant_row = unseen_df.sample(1).iloc[0]
    st.session_state.seen_plants.append(plant_row.name)
    st.session_state.current_plant = plant_row

    correct_name = plant_row["name"]
    
    # Optional category filtering if 'category' column exists
    if "category" in df.columns:
        plant_category = plant_row["category"]
        same_category_df = df[(df["category"] == plant_category) & (df["name"] != correct_name)]
        if len(same_category_df) < 3:
            wrong_pool = df[df["name"] != correct_name]
        else:
            wrong_pool = same_category_df
    else:
        wrong_pool = df[df["name"] != correct_name]

    wrong_options = wrong_pool.sample(min(3, len(wrong_pool)))

    options = list(wrong_options["name"]) + [correct_name]
    random.shuffle(options)
    st.session_state.options = options
    st.session_state.answered = False


# Trigger first question if none is active and we haven't finished
if st.session_state.current_plant is None and len(st.session_state.seen_plants) < len(df):
    get_next_question()

# 3. Check if quiz is finished
if len(st.session_state.seen_plants) >= total_plants and (st.session_state.current_plant is None):
    st.balloons()
    st.success("🎉 You've gone through all the plants in the database!")
    st.metric(
        label="Final Score",
        value=f"{st.session_state.score} / {total_plants}",
    )

    if st.button("🔄 Restart Quiz"):
        st.session_state.seen_plants = []
        st.session_state.score = 0
        st.session_state.current_plant = None
        st.rerun()

elif st.session_state.current_plant is not None:
    plant = st.session_state.current_plant
    plant_id = plant["id"]

    img_paths = get_plant_images(plant_id)

    current_progress = len(st.session_state.seen_plants)
    st.sidebar.progress(
        current_progress / total_plants,
        text=f"Progress: {current_progress}/{total_plants} (Score: {st.session_state.score})",
    )
    
    if "category" in plant and pd.notna(plant["category"]):
        st.sidebar.info(f"Kategoria: **{plant['category']}**")

    # Display the found image(s)
    if img_paths:
        if len(img_paths) > 1:
            cols = st.columns(len(img_paths))
            for idx, img_path in enumerate(img_paths):
                with cols[idx]:
                    try:
                        st.image(img_path, use_container_width=True)
                    except Exception:
                        st.warning(f"Nie można załadować: {img_path}")
        else:
            try:
                st.image(img_paths[0], width=400)
            except Exception:
                st.warning("Nie można załadować zdjęcia.")
    else:
        st.warning(
            f"Nie znaleziono zdjęć dla ID: {plant_id} w folderze images/ (szukano plików o nazwie np. {plant_id}.jpg lub {plant_id}_*.jpg)."
        )

    # Quiz Form / Options
    with st.form("quiz_form"):
        choice = st.radio("Wybierz odpowiedź:", st.session_state.options, index=None)
        submitted = st.form_submit_button("Sprawdź")

    if submitted:
        st.session_state.answered = True
        if choice == plant["name"]:
            st.session_state.score += 1
            st.success("Poprawnie! 🎉")
        else:
            st.error(f"Błąd! To jest **{plant['name']}**.")

    # Next Question Button
    if st.session_state.answered:
        if st.button("Następna Roślina ➡️"):
            get_next_question()
            st.rerun()
