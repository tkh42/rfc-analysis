import torch
import numpy as np

import pandas as pd
from pathlib import Path
from tqdm import tqdm
from datasets import Dataset
from sentence_transformers import SentenceTransformer


class HFSTIndex:
    def __init__(
        self,
        dataframe: pd.DataFrame,
        index_encoder="all-mpnet-base-v2",  # to create index
        query_encoder=None,  # to encode query, defaults to index_encoder
        index_src_col="descriptions",  # text col name on which index to create
        index_col_name="embeddings",  # col name for index embeddings
        overwrite_existing=False,  # set True to force rebuilding of index
    ):

        self.dataset = Dataset.from_pandas(dataframe)

        self.index_encoder = None
        self.query_encoder = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_encoders(index_encoder, query_encoder)

        self.index_src_col = index_src_col
        self.index_col_name = index_col_name

        self.faiss_file = self._create_filename(index_encoder)
        if overwrite_existing:
            self.faiss_file.unlink(missing_ok=True)

        if self.faiss_file.exists():
            print("Loading existing faiss index...")
            self.dataset.load_faiss_index(
                index_name=self.index_col_name,
                file=self.faiss_file,
            )
            print("Faiss index loaded.")
        else:
            self._create_faiss_index()

    def _load_encoders(self, index_encoder, query_encoder):
        print("Loading encoders...")
        self.index_encoder = SentenceTransformer(index_encoder).to(self.device)
        self.query_encoder = self.index_encoder
        if query_encoder is not None and query_encoder != index_encoder:
            self.query_encoder = SentenceTransformer(query_encoder).to(self.device)
        print("Encoders loaded.")

    def _create_filename(self, index_encoder):
        faiss_file = f"{index_encoder}.faiss"
        return Path(faiss_file)

    def _create_faiss_index(self):
        def create_embeddings(ex):
            encoded = self.index_encoder.encode(ex[self.index_src_col])
            return {self.index_col_name: encoded}

        if not self.faiss_file.exists():
            with torch.no_grad():
                print("Creating embeddings...")
                data = self.dataset.map(create_embeddings)
                print("Creating faiss index...")
                data.add_faiss_index(column=self.index_col_name)
                print("Saving faiss index to disk...")
                data.save_faiss_index(
                    index_name=self.index_col_name,
                    file=self.faiss_file,
                )
                print("Faiss index saved.")

        print("Loading faiss index...")
        self.dataset.load_faiss_index(
            index_name=self.index_col_name,
            file=self.faiss_file,
        )
        print("Faiss index loaded.")

    def semantic_search(self, queries, k=10):
        with torch.no_grad():
            queries = self.query_encoder.encode(queries)
            queries = np.atleast_2d(queries)

        scores, searches = self.dataset.get_nearest_examples_batch(
            index_name=self.index_col_name,
            queries=queries,
            k=k,
        )

        return searches, scores