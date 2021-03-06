import os
import pickle
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

HEADER_NAMES = {
    'SEA': [
        'attribute_1',
        'attribute_2',
        'attribute_3',
        'label'
    ],
    'KDD': [
        'duration',
        'protocol_type',
        'service',
        'flag',
        'src_bytes',
        'dst_bytes',
        'land',
        'wrong_fragment',
        'urgent',
        'hot',
        'num_failed_logins',
        'logged_in',
        'num_compromised',
        'root_shell',
        'su_attempted',
        'num_root',
        'num_file_creations',
        'num_shells',
        'num_access_files',
        'num_outbound_cmds',
        'is_host_login',
        'is_guest_login',
        'count',
        'srv_count',
        'serror_rate',
        'srv_serror_rate',
        'rerror_rate',
        'srv_rerror_rate',
        'same_srv_rate',
        'diff_srv_rate',
        'srv_diff_host_rate',
        'dst_host_count',
        'dst_host_srv_count',
        'dst_host_same_srv_rate',
        'dst_host_diff_srv_rate',
        'dst_host_same_src_port_rate',
        'dst_host_srv_diff_host_rate',
        'dst_host_serror_rate',
        'dst_host_srv_serror_rate',
        'dst_host_rerror_rate',
        'dst_host_srv_rerror_rate',
        'label'
    ],
}


class DataLoader:
    def __init__(self, data_path, percentage_historical_data=0.2):
        self.data_path = data_path
        self.percentage_historical_data = percentage_historical_data
        self.X = None
        self.y = None
        self.X_historical = None
        self.y_historical = None
        self.list_classes = None

    def return_data(self):
        """
        The data which is used for the streaming part emulation.
        :return: Tuple X and y
        """
        return self.X, self.y

    def return_historical_data(self):
        """
        The historical used for training the model before going online.
        :return:
        """
        return self.X_historical, self.y_historical

    def split_data(self):
        """
        Split the dataset based on the percentage given in argument (percentage_historical_data)
        """
        number_histocal_data = int(self.percentage_historical_data * len(self.X))
        self.X_historical = self.X[:number_histocal_data]
        self.y_historical = self.y[:number_histocal_data]
        self.X = self.X[number_histocal_data + 1:]
        self.y = self.y[number_histocal_data + 1:]

    def normalization(self):
        """
        Normalized the data based on the historical data. Since we study concept drift we prefer to use a MinMax
        normalisation.
        """
        mms = MinMaxScaler()
        self.X_historical = mms.fit_transform(self.X_historical)
        self.X = mms.transform(self.X)

    def save_data(self, path):
        if not os.path.exists(path):
            with open(self.data_path, 'wb') as data_file:
                data = {'X': self.X, 'y': self.y, 'X_historical': self.X_historical, 'y_historical': self.y_historical}
                pickle.dump(data, data_file, protocol=pickle.HIGHEST_PROTOCOL)

    def load_from_pickle(self):
        with open(self.data_path, 'rb') as data_file:
            data = pickle.load(data_file)
            self.X = data['X']
            self.y = data['y']
            self.X_historical = data['X_historical']
            self.y_historical = data['y_historical']

    def get_classes(self):
        return self.list_classes


class SEALoader(DataLoader):
    def __init__(self, sea_data_path, use_pickle_for_loading=False, percentage_historical_data=0.2):
        DataLoader.__init__(self, sea_data_path, percentage_historical_data=percentage_historical_data)
        if use_pickle_for_loading:
            self.load_from_pickle()
        else:
            sea_df = pd.read_csv(self.data_path, header=None, names=HEADER_NAMES['SEA'])
            sea_data = sea_df.values
            self.X = sea_data[:, 1:3]
            self.y = sea_data[:, -1]
            self.list_classes = np.unique(self.y)
            DataLoader.split_data(self)
            DataLoader.normalization(self)
            # Normalization
            mms = MinMaxScaler()
            self.X = mms.fit_transform(self.X)


class KDDCupLoader(DataLoader):
    """
    This data set was used in KDD Cup 1999 Competition (Frank and Asuncion, 2010). The full dataset has about five
    million connection records, this is a set with only 10 % of the size. The original task has 24 training attack
    types. The original labels of attack types are changed to label abnormal in our experiments and we keep the label
    normal for normal connection. This way we simplify the set to two class problem.
    """
    def __init__(self, kdd_data_path, use_pickle_for_loading=False, percentage_historical_data=0.2, dummies=True):
        '''

        :param kdd_data_path:
        :param use_pickle_for_loading: You have registered a pickle file
        :param percentage_historical_data: Percentage of data to use for the historical training.
        :param dummies: If true convert categorical variable into dummy/indicator variables (one-hot encoded).
        Use dummies equal false when your learning algorithm is DecisionTree.
        :return:
        '''
        DataLoader.__init__(self, kdd_data_path, percentage_historical_data=percentage_historical_data)
        if use_pickle_for_loading:
            self.load_from_pickle()
        else:  # TODO shorten the following lines of code
            kdd_df = pd.read_csv(
                self.data_path,
                index_col=False,
                delimiter=',',
                header=None,
                names=HEADER_NAMES['KDD']
            )
            # TODO (minor) : Do not load these 2 columns at first
            useless_features = ["num_outbound_cmds", "is_host_login"]
            kdd_df = kdd_df.drop(useless_features, axis=1)

            # Handle symbolic data
            symbolic = [
                "protocol_type",
                "service",
                "flag",
                "label"
            ]

            self.symbolic_df = kdd_df[symbolic]
            if dummies:
                symbolic_df_without_label = self.symbolic_df[self.symbolic_df.columns.difference(['label'])]
                dummies_df = pd.get_dummies(symbolic_df_without_label)
                non_categorical = kdd_df[kdd_df.columns.difference(symbolic)].values
                # Create X
                self.X = np.concatenate((non_categorical, dummies_df.values), axis=1)
                # Create y
                label = self.symbolic_df['label'].values
                self.y = LabelEncoder().fit_transform(label)
                self.list_classes = np.unique(self.y)
                DataLoader.split_data(self)
                DataLoader.normalization(self)
            else:
                self.__encode_symbolic_df()
                kdd_df[symbolic] = self.symbolic_df
                self.X = kdd_df[kdd_df.columns.difference(['label'])].values
                self.y = kdd_df['label'].values
                self.list_classes = np.unique(self.y)
                DataLoader.split_data(self)

    def __encode_symbolic_df(self):
        self.symbolic_encoder = defaultdict(LabelEncoder)
        # Encode the symbolic variables
        self.symbolic_df = self.symbolic_df.apply(lambda x: self.symbolic_encoder[x.name].fit_transform(x))

    def inverse_encode_symbolic_df(self):
        self.symbolic_df.apply(lambda x: self.symbolic_encoder[x.name].inverse_transform(x))


class UsenetLoader(DataLoader):
    '''
    Text dataset, inspired by Katakis et al. (2010), is a simulation of news filtering with a concept drift related to
    the change of interest of a user over time. For this purpose we use the data from 20 Newsgroups (Rennie, 2008) and
    handle it as follows. There are six topics chosen and the simulated user in each concept is subscribed to mailing
    list of four of them being interested only in two. Over time the virtual user decides to unsubscribe from those
    groups that he was not interested in and subscribe for two new ones that he becomes interested in. The previously
    interesting topics become out of his main interest. The Table 1 summarizes the concepts. Note that the topics of
    interest are repeated to simulate recurring concepts. The original dataset is divided into train and test. Data from
    train appears in the first three concepts whereas data from test is in the last three (recurring) concepts.
    The data is preprocessed with tm (Feinerer, 2010) package for R keeping only attributes (words) longer than three
    letters and with minimal document frequency greater than three. Moreover, from the remaining only those that are
    informative are kept (entropy > 75 x 10-5 ). Attribute values are binary indicating the presence or absence of the
    respective word. At the end the set has 659 attributes and 5,931 examples.
    '''

    def __init__(self, sea_data_path, use_pickle_for_loading=False, percentage_historical_data=0.2):
        DataLoader.__init__(self, sea_data_path, percentage_historical_data=percentage_historical_data)
        if use_pickle_for_loading:
            self.load_from_pickle()
        else:
            usenet_df = pd.read_csv(self.data_path, header=None)
            d = {'no': 0., 'yes': 1., 't': 1., 'f': 0., 'tt': 1}  # tt = error in the df
            usenet_data = usenet_df.replace(d).values
            self.X = usenet_data[:, :-1]
            self.y = usenet_data[:, -1]
            self.list_classes = np.unique(self.y)
            DataLoader.split_data(self)

