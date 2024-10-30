import pickle
import os
import pandas as pd

from tqdm import tqdm
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()


# Function to get embedding for a single text (replace 'your-model-name' with your OpenAI model)
def get_embedding(text, model="text-embedding-3-small"):
    embeddings = OpenAIEmbeddings(model=model, api_key=os.getenv("OPENAI_API_KEY"))
    vectors = embeddings.embed_query(text)
    return vectors


# Function to save embeddings to a pickle file
def save_embeddings_to_pickle(embedding_dict, filename):
    assert filename.endswith(".pkl"), "확장자는 '.pkl'이어야 합니다."
    try:
        # Load existing embeddings to avoid overwriting
        existing_embeddings = load_embeddings_from_pickle(filename)
    except FileNotFoundError:
        existing_embeddings = {}

    # Merge new embeddings into existing ones
    existing_embeddings.update(embedding_dict)

    # Save the updated embeddings
    with open(filename, "wb") as file:
        pickle.dump(existing_embeddings, file)


# Function to load embeddings from a pickle file
def load_embeddings_from_pickle(filename: str):
    assert filename.endswith(".pkl"), "확장자는 '.pkl'이여야 합니다"
    try:
        with open(filename, "rb") as file:
            return pickle.load(file)
    except FileNotFoundError:
        return {}


# Function to update embeddings with new records
def update_new_embeddings(new_records, filename):
    assert filename.endswith(".pkl"), "확장자는 '.pkl'이여야 합니다"

    # Load existing embeddings
    existing_embeddings = load_embeddings_from_pickle(filename)

    # Iterate over new records and add new embeddings
    count = 0
    new_count = 0
    new_embeddings = {}
    for record_id, text in tqdm(new_records.items()):
        if record_id not in existing_embeddings:
            # Get embedding for the new text
            embedding = get_embedding(text)
            # Add the new embedding to the existing embeddings
            new_embeddings[record_id] = embedding
            count += 1
            new_count += 1

            if count % 100 == 0:
                save_embeddings_to_pickle(
                    {**existing_embeddings, **new_embeddings}, filename
                )
                count = 0
                new_embeddings = {}

    # Save the updated embeddings to the pickle file
    if new_embeddings:
        save_embeddings_to_pickle({**existing_embeddings, **new_embeddings}, filename)
    print(f"{new_count} Embedding(s) updated successfully.")


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f", "--file", required=True, help="CSV file containing records"
    )
    parser.add_argument(
        "-tc", "--text_column", required=True, help="Column containing text data"
    )
    parser.add_argument(
        "-ic", "--id_column", required=True, help="Column containing unique IDs"
    )
    parser.add_argument(
        "-p", "--pickle_path", required=True, help="Path of pickle to update"
    )

    args = parser.parse_args()

    df = pd.read_csv(args.file)
    text_column = args.text_column
    id_column = args.id_column
    pickle_path = args.pickle_path

    df[text_column].fillna("", inplace=True)
    filtered_df = df[df[text_column] != ""]

    # Convert to a dictionary with 'id_column' as keys and 'text_column' as values
    new_records = filtered_df.set_index(id_column)[text_column].to_dict()

    # Update the embeddings
    update_new_embeddings(new_records, filename=pickle_path)
