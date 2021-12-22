__author__ = 'Sebastien levy'
import pandas as pd
from sklearn import preprocessing, decomposition
import numpy as np

class ADOS_Data(pd.DataFrame):
    def __init__(self, *args, **kwargs):
        super(ADOS_Data, self).__init__(*args, **kwargs)
        self.n_col = self.shape[1]-1
        self.scaling = 3


    def full_preprocessing(self, normalize, missing_strat, process_strat, label_age, label_gender, label_id,
                      print_missing=True, print_columns=False, poly_degree=2):

        self.preprocessing(label_id)

        if normalize:
            self.normalize_age(label_age, label_gender)

        # We print the distribution of missing values (8)
        if print_missing:
            print('printing missing')
            missing_val_columns = self.apply(pd.value_counts)[8:]
            pd.set_option('display.max_columns', missing_val_columns.shape[1])
            print(missing_val_columns)
            pd.reset_option('display.max_columns')

        if missing_strat == 'Binary':
            # We create the binary columns
            self.create_missing_data_col()

        if missing_strat in ['Replacement', 'Binary']:
            # We replace missing values in the ADOS answers (8) by 0
            self.replace(8, 0, inplace=True)

        if print_columns:
            print(self.columns)
        if process_strat in ['pca_comp']:
            self.create_components_feat()
        if process_strat in ['indicator','interaction_ind']:
            self.create_indicators_columns()
        if process_strat in ['poly','interaction_ind']:
            self.create_poly_columns(poly_degree)
        if print_columns:
            print(self.columns)
        self.drop_constant_columns()

    def getAdos(self):
        return self.n_col - 2

    @classmethod
    def read_csv(cls, directory, *args, **kwargs):
        return cls(pd.read_csv(directory, *args, **kwargs))

    def select_good_columns(self, columns_of_interest, keep_the_column=False):
        if keep_the_column:
            self[:] = self[columns_of_interest]
            self.dropna(axis=1, inplace=True)
            self.n_col = len(columns_of_interest)
        else:
            self.drop(self[columns_of_interest], axis=1, inplace=True)
            # self.drop(self[[0]], axis=1, inplace=True)
            self.drop(self[['Unnamed: 0']], axis = 1, inplace = True)
            print('hello!')
            print(self)
            self.n_col = self.n_col - len(columns_of_interest)

    def preprocessing(self, label_id, replace_gender_letter=False):
        if replace_gender_letter:
            self.replace(['M','F'], [0,self.scaling], inplace=True)
        self.dropna(axis=0, how="all", inplace=True)
        self.dropna(axis=0, how="any", subset=[label_id], inplace=True)
        self.fillna(8, inplace=True)
        self.labels = self[label_id]
        # self.drop(label_id, axis=1, inplace=True)

    def normalize_age(self, label_age, label_gender):
        min_max_scaler = preprocessing.MinMaxScaler(feature_range=(0,self.scaling))
        self[label_age] = min_max_scaler.fit_transform(self[label_age].values.reshape(-1,1))
        self[label_gender] = self.scaling*self[label_gender]

    def create_missing_data_col(self, missing_val = 8):
        for col in self.columns:
            if missing_val in self[col].unique():
                self[col+'_miss'] = [int(x == missing_val)*self.scaling for x in self[col]]

    def create_poly_columns(self, degree=2, interaction_only=True):
        if degree == 2:
            for col1 in self.columns[:self.n_col-1]:
                for col2 in self.columns[:self.n_col-1]:
                    if col1 == col2 and not interaction_only:
                        self[col1+'^2'] = self[col1]*self[col1] / self.scaling
                    if col1 < col2:
                        self[col1+'x'+col2] = self[col1]*self[col2] / self.scaling

    def create_indicators_columns(self, thres=[1,2,3], delete_original = True, are_counted_col=True):
        for col in self.columns[:self.getAdos()-1]:
            for t in thres:
                self[col+">="+str(t)] = (self[col] >= t) *self.scaling
            if delete_original:
                self.drop(col, axis=1, inplace=True)
        # We add the indicators columns if they are counted columns
        if are_counted_col:
            self.n_col = self.getAdos()*(len(thres)+1-int(delete_original))+2
        else:
            self.n_col = self.getAdos()*(1-int(delete_original))+2

    def create_components_feat(self, components=[1,2,3]):
        spca = decomposition.SparsePCA(alpha=0.02)
        length = self.shape[1]
        print(self)
        data = spca.fit_transform(self)
        for comp in components:
            self['PCA_comp_'+str(comp)] = data[:,comp]

    def getGroupsBy(self, valuesList, by, by2=None):
        """
        With the by values (and by2 when not None), it creates a group for each value in the valuesList
        If some rows of the dataframe don't have values in the valuesList for by, they will be ignored, and a text will be printed
        :param valuesList: the list of values (or tuples if by different from None)
        :param by: the column to look at when dividing in groups
        :param by2: when not None, the other column to look at
        :return: the list of groups
        """
        valueInd = []
        for values in valuesList:
            valueInd.append([])
        for index in self.index:
            for i, values in enumerate(valuesList):
                if by2 is None:
                    if self.loc[index, by] in values:
                        valueInd[i].append(index)
                        break
                else:
                    if (self.loc[index, by],self.loc[index,by2]) in values :
                        valueInd[i].append(index)
                        break
            else:
                print('ERROR')
                print('--> index: '+str(index))
                print('--> value: '+str(self.loc[index, by]))
                print(valuesList)
                print('\n')
        groups = []
        for indexList in valueInd:
            if indexList == []:
                continue
            groups.append(ADOS_Data(self.loc[indexList]))
        return groups

    def missingValuesColumns(self):
        """
        :return: the columns with missing data
        """

        columnIndices = self.isnull().any(axis=0)
        return self.columns[columnIndices]

    def drop_constant_columns(self):
        self.loc[:, (self != self.loc[0]).any()]

    def print_full(self):
        pd.set_option('display.max_rows', len(self))
        print(self)
        pd.reset_option('display.max_rows')

    def scale(self, scalings):
        for i, scaling in enumerate(scalings):
            self.iloc[:,i] = self.iloc[:,i]/scaling

def get_ease_score(filename, feature_set, thres=None):
    res = pd.read_csv(filename)
    res['Code'] = [(s[0] + s[2]).upper() if s[1] == '0' else s.upper() for s in res['Code']]
    res.index = res['Code']
    res[:] = res[['Score']]
    res.dropna(axis=1, inplace=True)

    bad_columns= []
    if thres is not None:
        bad_columns = list(res[res['Score'] >= thres].index)

    if feature_set == [] or feature_set is None:
        res['Score'].drop(res[bad_columns], axis=1, inplace=True)
        bad_columns.append(['{}_miss'.format(f) for f in bad_columns])
        return np.concatenate((np.array(res['Score']), [0.5,0.5], np.array(res['Score']))), bad_columns
    else:
        ease = []
        for feat in feature_set:
            if 'age' in feat or 'male' in feat:
                ease.append(0.5)
            elif '_' in feat:
                if feat.split('_')[0] not in bad_columns:
                    ease.append(res.at[feat.split('_')[0], 'Score'])
                else:
                    bad_columns.append(feat)
            elif feat not in bad_columns:
                ease.append(res.at[feat, 'Score'])
        return ease, [f for f in bad_columns if f in feature_set]

if __name__ == '__main__':
    ease_score = get_ease_score('m3_ease_of_scoring.csv', ['A2', 'A4', 'A8', 'B2', 'B7', 'B8', 'D4', 'male', 'B3_miss', 'D3_miss'], 6)
    print(ease_score)
    df = ADOS_Data([[1,2,3], [4,5,6], [7,7,8], [5,4,3]], index=['a', 'b', 'c', 'd'], columns=['small', 'middle', 'big'])
    print(df)
    df.scale([2,3,6])
    print(df)