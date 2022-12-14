# -*- coding: utf-8 -*-
"""GA_Hyperparameters_Optimization
GA -
* Weight optimization
* Hyperparameter tuning
* Feature selection
* Model performance optimization
* Time optimization

Genetic Algorithm -
 * Randomly initialize a population
 * Evaluate fitness of population
 * Repeat
---

* Select parents from population
* Crossover on parents for creating new set of population
* Mutation on the population
* Evaluate fitness of population

---
Repeat - repeat until best solution is provided

Feature Selection & Hyperparameter Optimization
1. Choose the features first
2. Optimize the hyperparameters accordingly
"""

import numpy as np 
import pandas as pd 
import numpy.random as rnd 
from scipy import spatial

from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import VarianceThreshold
from sklearn import metrics


from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import ElasticNet
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

#from sklearn.utils.testing import ignore_warnings
#from sklearn.exceptions import ConvergenceWarning


import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import seaborn as sns

df_train = pd.read_csv("/content/drive/MyDrive/GA_Project/Feature_Selection+Optimization/dataset/train.csv", index_col = "ID")
df_test = pd.read_csv("/content/drive/MyDrive/GA_Project/Feature_Selection+Optimization/dataset/test.csv", index_col = "ID")

"""The shape of the training data file. TARGET values portion, 0 - 96% & 1 - 4% """

print("{} rows and columns".format(*df_train.shape))
df_train.TARGET.value_counts(normalize = True)

#DATATYPES 
display(df_train.dtypes.value_counts())

#Missing value available?
missing = df_train.isnull().sum().sum()
print("Missing entries in the dataset - ", missing)
df_train.var15.describe()

df_train.var3.describe()

display(df_train['var3'].value_counts(normalize=True)[0:3])
df_train['var3'] = df_train['var3'].replace(-999999,2)

df_train, df_val = train_test_split(df_train, test_size=0.2, random_state = 1989, stratify = df_train.TARGET, shuffle = True)
kfold = KFold(n_splits=5, random_state = 1989, shuffle = True) # 5-cross validation

fts_num = df_train.drop(axis =1, columns = ['TARGET']).select_dtypes(np.number).columns
print(fts_num)

#Standardisation and range scaler
fts_num = df_train.drop(axis =1, columns = ['TARGET']).select_dtypes(np.number).columns
transformed_num = Pipeline(steps = [('Standarise', StandardScaler()), ('MinMax', MinMaxScaler())])

preprocessor_preds = ColumnTransformer(transformers = [('num', transformed_num, fts_num)]) #cenre, scale, constrain range

#Transformation on training data
df_train_2 = pd.DataFrame(preprocessor_preds.fit_transform(df_train))
df_train_2.columns = fts_num

#Transformation on validation set
df_val_2 = pd.DataFrame(preprocessor_preds.fit_transform(df_val))
df_val_2.columns = fts_num

#Transformation on test set
df_test_2 = pd.DataFrame(preprocessor_preds.fit_transform(df_test))
df_test_2.columns = fts_num

#Concatenate preprocessed data

#TRAINING DATA
df_train = pd.concat([df_train_2, df_train.drop(axis=1, columns=fts_num).reset_index().drop(axis=1, columns=['ID'])], axis = 1)

#VALIDATION DATA
df_val = pd.concat([df_val_2, df_val.drop(axis=1, columns=fts_num).reset_index().drop(axis=1, columns=['ID'])], axis = 1)

# TEST DATA
df_test = pd.concat([df_test_2, df_test.drop(axis=1, columns=fts_num).reset_index().drop(axis=1, columns=['ID'])], axis = 1)

#FAKA KORO
del df_train_2, df_val_2, df_test_2, fts_num, transformed_num, preprocessor_preds

"""OPTIMIZATION(ga)"""

def f_random_candidates(features_name, population, hyperparams, output_type, df_pop=False):
    '''create an initial population'''
   
    # Create solution for features
    if output_type == 'feature':
        
        # Initial population will have between 10-91% of features
        feature_size = rnd.choice(a=range(10,91),size=population, replace=True)
        feature_size = [np.round(pct / 100 * len(features_name)) for pct in feature_size]
        
        # Create a list of feature positions for each candidate
        selection = [rnd.choice(a=range(0,len(features_name)-1), replace=False, size=cols.astype('int')) \
                     for cols in feature_size]
        
        selection = [list(selection[i]) for i in range(len(selection))]
        
        # Return
        return selection
    
    # Create solution for hyperparameters
    elif (output_type == 'hyperparams') & (hyperparams != False):
        
        # Generate random numbers in range for each hyperparameter
        random_hyperparams = []
        for j in range(len(hyperparams['names'])):
            temp = (np.random.uniform(hyperparams['min_value'][j],
                                      hyperparams['max_value'][j],
                                      population))
            random_hyperparams.append(temp)
        
        # Get length of features
        n_features = df_pop['features'].apply(len).tolist()

        # Store hyperparameters in diction
        hyperparam_vals = []
        for i in range(population):
            val = {'name':[],'value':[]}
            for j in range(len(hyperparams['names'])):
                val['name'].append(hyperparams['names'][j])
                temp = random_hyperparams[j][i]
                if hyperparams['type'][j] == 'int':
                    temp = np.int64(round(temp))
                if hyperparams['names'][j] == 'max_features':
                    temp = min(temp, n_features[i])
                val['value'].append(temp)           
            
            hyperparam_vals.append(val)
            del val

        # Return
        return hyperparam_vals

"""**CROSSOVER** 

-- FEATURES -

1. Randomly generate a crossover point(firs_faeture, last_feature)
2. Weighted sampling of the previous generation's solutions and select 2 parents
3. Create a child solution which have all the features before the cross point from first parent and all the features from the second parent after the cross point.

-- HYPERPARAMETERS - 

1. Weighted sample of previous generation solutions of the size of the number of hyperparameters
2. Randomly choose which hyperparameter to take from which parent solution
3. Create the child hyperparameters from the choosen parent solution
"""

def f_gen_child_crossover(df, features_name, hyperP, output_type):
    '''Mutate 2 parents to create a child'''
    
    # Crossover features
    if output_type == 'feature':
        
        # Create an integer list of features
        l_features = list(range(0,len(features_name)))
        cross_point = np.int(rnd.randint(low=0, high=len(features_name), size=1))
        
        # Extract Two Parents
        selection = np.random.choice(df.features, 
                                     size=2, 
                                     replace=False, 
                                     p=df.probability)     
        par1 = list(selection[0])
        par2 = list(selection[1])
            
        # Convert to Boolean
        par1 = [item in par1 for item in l_features]
        par2 = [item in par2 for item in l_features]
        
        # Single point cross over and convert to indices
        child = par1[0:cross_point] + par2[cross_point:]
        child = [i for i,x in enumerate(child) if x == True]    
        
        return child   
  
    elif (output_type == 'hyperparams') & (hyperP != False):  
        # Identify the number of parameters
        n_hyperP = len(hyperP['min_value'])
        # Extract n Parents
        selection = np.random.choice(df.hyperparameters, 
                                     size=n_hyperP, 
                                     replace=False, 
                                     p=df.probability)  
        
        # Randomly choose which parent to select each parameter from
        parent_choice = list(np.random.choice(range(n_hyperP),
                                              size = n_hyperP,
                                              replace=False))        
        # Copy the parent as the child
        child = selection[0]
        # Update child vector with choosen parent
        for i in range(n_hyperP):
            child['value'][i] = selection[parent_choice[i]]['value'][i]

        return child

"""**MUTATION**

Features:

1. For each feature in the dataframe, generate a random number between 0 and 1
2. If the generated probability is below the user stated mutation rate, then reverse the switch for that column (i.e. if a feature is included then remove it and vice versa).

Hyperparameters:
1. For each hyperparameter in the choosen model, generate a random number between 0 and 1
2. If the random number is below the user stated mutation rate, the generate a random number between a stated range

3. Finally check if the hyperparameter is outside of the min-max range and reduce it to that range if necessary
"""

def f_gen_child_mutate(candidate, features_name, p_mutate, hyperP, output_type, hyperparams_increment):
    if output_type == 'feature':        
        # Create an integer list of features
        l_features = list(range(0,len(features_name)))
        
        # Convert feature into boolean vector
        candidate = [item in candidate for item in l_features]
        
        # Conditionally mutate features in chromosome (reverse binary flag)          
        candidate_new = []
        for item in candidate:
            if rnd.rand() <= p_mutate:
                candidate_new.append(not item)
            else:
                candidate_new.append(item)
                
        # Convert to indicies
        candidate_new = [i for i,x in enumerate(candidate_new) if x == True]     
        return candidate_new
    
    elif (output_type == 'hyperparams') & (hyperP != False):
        
        # Identify size of mutation
        v_mutate = (np.random.uniform((1-hyperparams_increment), (1+hyperparams_increment), 1)).item()
        
        # Identify Min and Max for parameters
        l_min =  hyperP['min_value']
        l_max =  hyperP['max_value']
        
        # Identify the number of parameters
        n_hyperP = len(l_min)
        
        # Probabilistically mutate certain parameters
        candidate_new = []       
        for i in range(n_hyperP):
            if rnd.rand() <= p_mutate:   
                temp = candidate['value'][i] * v_mutate
                if hyperP['type'][i] == 'int':
                    temp = np.int64(round(temp))                
                candidate_new.append(temp)
            else:
                candidate_new.append(candidate['value'][i])
        
        # Ensure that value is between ranges
        for i in range(n_hyperP):
            if (candidate_new[i] < l_min[i]):
                candidate_new[i] = l_min[i]
            elif (candidate_new[i] > l_max[i]):    
                candidate_new[i] = l_max[i]

        # Update values                
        candidate['value'] = candidate_new
        return candidate

# Function to generate a population of candidates
def f_generate_population(inital_flag, population, features_name, p_crossover, p_mutate, hyperparams, hyperparams_increment, hyperparams_multiple, df=False, generation=0, initalise=False):
    '''Generates all candidates in population'''
    # Create initial population
    if inital_flag == True:   
        # Check if there is an initial solution & reduce, population by one if there is
        if initalise != False:
            population = population - 1
        
        # generate random features
        df_pop = pd.DataFrame({'generation':generation,
                               'candidate':range(0,population),
                               'features': random_candidate(features_name,
                                                              population,
                                                              hyperparams,
                                                              output_type = 'feature')})
        
        # Duplicate rows for population range
        df_pop = df_pop.loc[df_pop.index.repeat(hyperparams_multiple)]
        
        # Generate population
        df_pop['hyperparameters'] = random_candidate(features_name=features_name,
                                population = population * hyperparams_multiple,
                                hyperparams=hyperparams,
                                output_type = 'hyperparams',
                                df_pop=df_pop)
    
        # If Initial solution then add in
        if initalise != False:
            df = pd.DataFrame({'generation':generation,
                               'candidate':range(population, population + 1),
                               'features':[initalise['features']],
                               'hyperparameters':[initalise['hyperparameters']]},
                              index=[population])
            
            df_pop = df_pop.append(df)
        
        
        # Reset Index
        df_pop.index = range(0, population * hyperparams_multiple)
        
        # Return
        return df_pop
    else:
        # Distribute the population
        population_crossover = round(population * p_crossover)
        population_remainder = population-population_crossover
        
        # ----- Create crossover candidates -----
        
        # Create crossover populate for feature selection
        df_pop = pd.DataFrame({'generation':generation,
                               'candidate':range(0,population_crossover)})
        df_pop['features'] = [f_gen_child_crossover(df=df, features_name=features_name, hyperparams=hyperparams, output_type = 'feature') \
                              for _ in range(population_crossover)]
            
        # Duplicate rows for population range
        df_pop = df_pop.loc[df_pop.index.repeat(hyperparams_multiple)]
            
        # Create crossover population for hyperparameters
        df_pop['hyperparameters'] = [f_gen_child_crossover(df=df, features_name=features_name, hyperparams=hyperparams, output_type = 'hyperparams') \
             for _ in range(population_crossover * hyperparams_multiple)]
           
        # Reset Index
        df_pop.index = range(0, population_crossover * hyperparams_multiple)        
                
        # ----- Create Randomly Selected candidates ----- 
        # Initialise population
        df_temp = pd.DataFrame({'generation':generation,
                                'candidate':range(population_crossover, 
                                                  population)})   
        # Randomly select candidates
        selected_index = \
            df.sample(n=population_remainder,
                      replace = False, 
                      weights=df.probability).candidate.tolist()        
        
        # Extract hyperparameters
        selected_features = df.iloc[selected_index,:].features.tolist()
        selected_params = df.iloc[selected_index,:].hyperparameters.tolist()
        
        # Update temp dataframe
        df_temp['features'] = [selected_features[i] 
                               for i in range(len(selected_features))]
        df_temp['hyperparameters'] = [selected_params[i] 
                               for i in range(len(selected_params))]        
        
        # Duplicate rows for population range
        df_temp = df_temp.loc[df_temp.index.repeat(population_remainder)]
        
        # Append to population dataframe
        df_pop = df_pop.append(df_temp,ignore_index=True)
        
        # Clear up
        del selected_features, selected_params, df_temp
        
        # ----- Mutate Population -----
        
        # Mutate existing candidate features
        df_pop['features'] = \
            df_pop.features.apply(f_gen_child_mutate, 
                                  features_name=features_name,
                                  p_mutate=p_mutate,
                                  hyperparams=hyperparams,
                                  output_type = 'feature',
                                  hyperparams_increment=hyperparams_increment)
        
        # Mutate existing candidate hyperparameters
        df_pop['hyperparameters'] = \
            df_pop.hyperparameters.apply(f_gen_child_mutate, features_name=features_name,
                                         p_mutate=p_mutate, hyperparams=hyperparams,
                                         output_type = 'hyperparams', hyperparams_increment= hyperparams_increment)      
        
        # ----- Hyperparameter fix -----
        if hyperparams != False:
        
            # Get length of features
            n_features = df_pop['features'].apply(len).tolist()
            
            # Hyperparameter fix            
            for i in range(population):
                for j in range(len(hyperparams['names'])):
                    if hyperparams['names'][j] == 'max_features':
                        if df_pop.hyperparameters[i]['value'][j] > n_features[i] :
                            df_pop.hyperparameters[i]['value'][j] = \
                                n_features[i]

        # Return
        return df_pop

"""Evaluation of the solutions (models) created in each generation. This includes conducting cross validation and calculating the average AUC across folds."""

#@ignore_warnings(category=ConvergenceWarning)
def f_fitness(model, eval_metric, features, target, 
              feature_idx, kfold, hyperparams):
    '''Evaluates fitness of proposed solution'''
        
    # Extract the hyperparameters
    n_hyperparams = len(hyperparams['name'])
    hyperparameters = {hyperparams['name'][0]:hyperparams['value'][0]}
    if n_hyperparams > 1:
        for i in range(n_hyperparams):
            tempparameters = {hyperparams['name'][i]:hyperparams['value'][i]}
            hyperparameters = {**hyperparameters, **tempparameters}
    
    # Determine CV strategy
    if kfold == False:
        kfold = 5
    else:
        kfold = kfold
    
    # Apply cross validation to the modells
    results = cross_val_score(model.set_params(**hyperparameters), 
                              features.iloc[:,feature_idx], 
                              target,
                              cv=kfold,
                              scoring=eval_metric)
    
    # Replace NA's with 0
    results[np.isnan(results)] = 0
    
    return results

"""The evaulation for each fold is then averaged to have a final score for that candidate solution (model)."""

# Apply evaluation score to current population
def f_evaluation_score(df, features, target, eval_metric, model,
                       kfold, hyperparams):
    '''Apply f_fitness to each candidate'''
    
    # Calculate the evaluation metric
    evaluation_score = []
    for val in range(0, len(df)):
        eval_score = f_fitness(model=model,
                               eval_metric=eval_metric,
                               features = features,
                               target=target,
                               feature_idx=df['features'][val],
                               kfold=kfold,
                               hyperparams=df['hyperparameters'][val])
        
        # Average evaluation metric across folds
        evaluation_score.append(eval_score.mean())
        
        # Clear object
        del eval_score
    
    # Clear object
    del val
    
    # return evaluation score
    return evaluation_score

"""Calculation of the similarity between each solution and the best solution based on the performance metric in a generation. Tracks how similar the generated solutions are becoming over time. 

1. Jaccard similarity - the feature selection element of the algorithm  
2. Cosine similarity - hyperparameter similarity.
3. (Jaccard + cosine) functions for each solution to get an estimate of their similarity. Creates a probability field which is very important for the population generation element of the algorithm. This probability is based on the fitness function and is used as the weighting function when selecting parent solutions.
"""

# Jaccard similarity
def f_j_sim(list1, list2):
    s1 = set(list1)
    s2 = set(list2)
    return float(len(s1.intersection(s2)) / len(s1.union(s2)))

# Cosine similarity
def f_c_sim(l_other, l_best_score): 
    # Extract hyperparameter values
    l_other = l_other['value']
    # calculate similarity        
    sim = 1 - spatial.distance.cosine(l_best_score, l_other)
    return sim

# Calculate similarity between candidates and probability for next gen selection
def f_sim_n_prob(df):
        
    # Calculate similarity of solutions with best solutions - Features
    l_best_score = df.features[df['fitness_score'].idxmax()]
    df['similarity_features'] = df['features'].apply(f_j_sim, list2=l_best_score)
    del l_best_score

    # Calculate similarity of solutions with best solutions
    l_best_score = df.hyperparameters[df['fitness_score'].idxmax()]['value']
    df['similarity_hyperparameters'] = df.hyperparameters.apply(f_c_sim, l_best_score=l_best_score)
    del l_best_score 
        
    # Calculate cumulative probability for future stages
    df['probability'] = (df['fitness_score'] / sum(df['fitness_score']))
    
    # return
    return df

"""This function adds the model performance data to storage as well as calculates the number of features included in the model. The function calls the previous solution evaluation functions in turn. One vital bit of functionality is that it allows the user to alter the fitness function from being purely focussed on the evaluation metric (AUC) to including the number of features as part of the modelling process. This ultimately allows the user to determine how important finding a simple model is compared to optimising purely for AUC."""

# Function to populate attributes of candidates
def f_population_features(df, features, target, desiriability,
                          eval_metric, model, kfold, hyperparams):
    '''Get features of all candidates in population'''
    
    # Calculate feature size for candidates
    df['feature_size'] = df['features'].apply(len)
    
    # Calculate evaluation score for candidates
    df['evaluation_score'] = f_evaluation_score(df, features, target, eval_metric, model, kfold, hyperparams)
    
    # Conditionally create desirability fitness score
    if desiriability != False:
        
        # Create scalars - Features
        v_lb_features = desiriability['lb'][1]
        v_ub_features = desiriability['ub'][1]
        v_s_features = desiriability['s'][1]
        
         # Create scalars - Evaluation Metric
        v_lb_eval = desiriability['lb'][0]
        v_ub_eval = desiriability['ub'][0]
        v_s_eval = desiriability['s'][0]        
        
        # Calculate desirability for features
        df['desire_features']  = [0 if x > v_ub_features else 1 
                                  if x < v_lb_features else 
                                      ((x-v_ub_features)/
                                       (v_lb_features-v_ub_features))**
                                      v_s_features 
                                  for x in df['feature_size']]
    
        # Calculate desirability for evaluation metric
        df['desire_eval']  = [0 if x < v_lb_eval else 1
                              if x > v_ub_eval else 
                                      ((x-v_lb_eval)/
                                       (v_ub_eval-v_lb_eval))**
                                      v_s_eval 
                              for x in df['evaluation_score']]
        
        # calculate fitness score
        df['fitness_score'] = (df['desire_features'] * df['desire_eval'])**0.5
        
        # Drop fields
        df = df.drop(columns=['desire_features', 'desire_eval'])

    else:        
        # calculate fitness score
        df['fitness_score'] = df['evaluation_score']
        
    # Return 
    return df

"""Wrapper function which controls the optimisation process in it's entiriety, it allows the user to state the parameters of the search including:

1. Evaluation metrics (any metric accepted by sklearn)
2. Which model to use e.g. Elasticnet
3. Which hyperparameters are associated with the model (set to false if model doesn't require hyperparameters)
4. Desirability (Do we want to optimise purely for the performance metric or do we want to induce model simplicity)
4. Cross over rate
5. Mutation rate
5. Elitism
6. Maximum generations without improvement
"""

# Main Optimisation Function
def f_model_optimisation(df, target_var, generations,  population, eval_metric, model, kfold=False, hyperparams_multiple = 3, hyperparams = False, 
                         desiriability=False,p_crossover=0.8, p_mutate=0.01, hyperparams_increment = 0.1, elitism=False, gens_no_improve = False, initalise = False):
    '''Function uses GA's to choose features and tune hyperparameters'''
    
    # Print Model Stats
    print('Model Initialisation')
    # Split features and target
    features = df.drop(target_var,axis=1)
    features_name = features.columns
    target = df[target_var]
    
    # First Generation
    # Generate inital candidate features solutions
    df_pop_cur = f_generate_population(inital_flag=True, population=population, features_name=features_name, p_crossover=p_crossover, 
                                       p_mutate=p_mutate, hyperparams=hyperparams, hyperparams_increment=hyperparams_increment,
                                       hyperparams_multiple=hyperparams_multiple, initalise=initalise)
    
    # Enrich candidate solutions with features
    df_pop_cur = f_population_features(df=df_pop_cur, features=features, target=target, desiriability=desiriability,
                                       eval_metric=eval_metric, model=model, kfold=kfold, hyperparams=hyperparams)
    
    # Extract best score for each candidate
    df_pop_cur = df_pop_cur.loc[df_pop_cur.reset_index().groupby(['candidate'])['fitness_score'].idxmax()]
    
    # Enrich candidate solutions with similarity & probability
    df_pop_cur = f_sim_n_prob(df_pop_cur)
    
    # Create search storage
    df_output = df_pop_cur.copy()

    # Print Model Stats
    print('Gen: 00' +
          ' - Generation Mean:' + str(round(df_output.fitness_score.mean(), 4)).zfill(4) +
          ' - Generation Best:' + str(round(df_output.fitness_score.max(), 4)).zfill(4) +
          ' - Global Best:' + str(round(df_output.fitness_score.max(), 4)).zfill(4)
          )
    
    # Track best solution
    if gens_no_improve != False:
        count = 0
        v_best = df_output.fitness_score.max()
    
    #Run additional generations 
    # Loop for additional generations
    for gen in range(1, generations):
                
        # Elitism 
        if elitism > 0:
            
            # Create a dataframe with elite candidates
            df_elite = df_output.nlargest(columns='fitness_score', n=elitism)
            df_elite['candidate'] = population - 1
            df_elite['generation'] = gen 
            df_elite = df_elite.drop(columns=['similarity_features', 
                                              'similarity_hyperparameters', 'probability'])
        # New Population
        
        # Generate next candidate solutions   
        df_pop_cur = f_generate_population(inital_flag=False, 
                                           generation = gen,
                                           population=(population-elitism),
                                           features_name=features_name,
                                           df=df_pop_cur,
                                           p_crossover=p_crossover,
                                           p_mutate=p_mutate,
                                           hyperparams=hyperparams,
                                           hyperparams_increment=hyperparams_increment,
                                           hyperparams_multiple=hyperparams_multiple
                                           )
        
        # Enrich candidate solutions with features
        df_pop_cur = f_population_features(df=df_pop_cur, 
                                           features=features, 
                                           target=target,
                                           desiriability=desiriability,
                                           eval_metric=eval_metric,
                                           model=model,
                                           kfold=kfold,
                                           hyperparams=hyperparams)
        
        # Add elite
        if elitism > 0:
            df_pop_cur = pd.concat([df_pop_cur, df_elite]).reset_index().drop(columns=['index'])
            del df_elite
               
        # Extract best score for each candidate
        df_pop_cur = df_pop_cur.loc[df_pop_cur.reset_index().groupby(['candidate'])['fitness_score'].idxmax()]        
        
        # Enrich candidate solutions with similarity & probability
        df_pop_cur = f_sim_n_prob(df=df_pop_cur)
        
        # Update Output
        df_output = df_output.append(df_pop_cur,ignore_index=True)
                
        # Print Model Stats
        print('Gen: ' + str(gen).zfill(2) +
              ' - Generation Mean:' + str(round(df_output[df_output.generation == gen].fitness_score.mean(), 4)).zfill(4) +
              ' - Generation Best:' + str(round(df_output[df_output.generation == gen].fitness_score.max(), 4)).zfill(4) +
              ' - Global Best:' + str(round(df_output.fitness_score.max(), 4)).zfill(4))
        
        # Track number of generations with no improvement
        if gens_no_improve != False:
            if df_output.fitness_score.max() > v_best:
                count = 0
                v_best = df_output.fitness_score.max()
            else:
                count += 1

            # Conditionally break loop
            if count == gens_no_improve:
                break

    return df_output

"""Model Optimisation
Now that our function is set up we can apply it to our data to see how successful this search will be. In this section we will apply the following models to our optimisaton process.

Models:

ElasticNet
XGBOOST
Within each model there will be a look at the two objectives of maximising AUC as well as inducing sparcity with models.

The research surrounding GA suggests that a good setting for the search is:

Crossover rate = 80%
Mutation rate = 1 or 2% (2% has been choosen)
In the book Feature Enginerring and Selection: A Practical Approach for Predictive Models the authors suggest that we should not employ elitism in our optimisation strategy. This ultimately means that the best solution isn't perfectly reserved for the next generation. The ethos here is to avoid getting stuck in a local maxima.

Beyond these default values there are a number of other settings which will be tweaked for the individual models based on time.


ElasticNet
ElasticNet allows us to apply regulisation to a regression model and has two hyperparameters which we can tune:

Alpha
L1 ratio
In the following subsections the optimisation will be run to optimise purely AUC and then to build a balanced model (good predictive power but as simple as possible).

Optimise AUC
The output below shows the AUC found by the GA, it was run for 5 generations with a population of 20 candidate models with 5 hyperparameters being produced for each cadidate solution. The hyperparameters are banded between a range of 0 & 0.01 for alpha and 0 and 1 for l1_ratio.

The output below shows the performance of the model of the generations, we can see that it generally achieves AUC scores in the high 70's.

*Note as I have not built a seed into the optimisation model it will produce slightly different results each time when run
"""

# Run Optimisation - Optimise for AUC
df_ENet_AUC = f_model_optimisation(df=df_train, target_var='TARGET', generations=7, population=20, p_crossover=0.8,
                                   p_mutate=0.02, hyperparams_increment=0.01, hyperparams_multiple = 5, eval_metric='roc_auc',
                                   kfold=False, model=ElasticNet(), hyperparams = { 'names':['alpha', 'l1_ratio'],
                                                                                    'min_value': [0, 0],
                                                                                    'max_value': [0.01, 1],
                                                                                    'type':['float', 'float']
                                                                                   })

"""XGBOOST
The final model which we will run through our optimisation is XGBOOST, again this model has multiple hyperparameters which can be tuned, the one's which will be focussed on are:

learning_rate = Control the weighting of new trees added to the model
max_depth = The maximum depth of a tree
min_child_weight = The minimum sum of weights of all observations required in a child
gamma = minimum loss reduction required to make a split
colsample_bytree = The fraction of columns to be randomly samples for each tree
Optimise AUC
The GA search was run for 5 generations with a population of 20 candidate models with 5 hyperparameter variants being produced for each cadidate solution. The hyperparameter ranges are:

learning_rate = [0.03, 0.3]
max_depth = [2, 15]
min_child_weight = [1, 7]
gamma = [0, 0.5]
colsample_bytree = [0.3, 0.7]
The output below shows the performance of the model across the generations, we can see that it generally achieves AUC scores in the low-mid 80's.
"""

# Run Optimisation - Optimise for AUC
df_xgb_AUC = f_model_optimisation(df=df_train,
                                  target_var='TARGET',
                                  generations=5, 
                                  population=20,
                                  p_crossover=0.8,
                                  p_mutate=0.02,
                                  hyperparams_increment=0.01,
                                  hyperparams_multiple = 5,
                                  eval_metric='roc_auc',
                                  kfold=False,
                                  model=XGBClassifier(objective="binary:logistic", scale_pos_weight = 25),
                                  hyperparams = {'names':['learning_rate', 'max_depth', 
                                                          'min_child_weight', 'gamma', 'colsample_bytree'],
                                                 'min_value': [0.03, 2,  1, 0,   0.3],
                                                 'max_value': [0.3,  15, 7, 0.5, 0.7],
                                                 'type':['float', 'int', 'int', 'float', 'float']}

"""Analysis Findings
The results for all candidate models assessed by the GA were stored and now can be investigated. The graphic below shows the mean and max AUC achieved by each model across the generations. We can see that the mean scores across the generations are generally increasing indicating that the GA is driving towards more similar solutions across generations. The max score doesn't necessarily increase between generations as it reflects accepting worse solutions to enter new parts of the search space.
"""

# Summarise EN scores
df_temp_EN = df_ENet_AUC.groupby('generation')['evaluation_score'].agg(['mean', 'max']).reset_index()
df_temp_EN['model'] = 'ElasticNet'

# Summarise XG scores
df_temp_XG = df_xgb_AUC.groupby('generation')['evaluation_score'].agg(['mean', 'max']).reset_index()
df_temp_XG['model'] = 'XGBOOST'

# Combine Dataframes
df_vis = pd.concat([df_temp_EN, df_temp_XG])

# Plot evaluation score
fig, ax = plt.subplots(1, 2, figsize=(16,6))
fig.suptitle("Average and Best Evaluation Scores Per Generation", fontsize=16)    
ax[0].set_title("ELasticNet")
ax[1].set_title("XGBOOST")
sns.lineplot(data = df_temp_EN, x= 'generation', y='mean', color="blue", label='Mean', ax = ax[0])
sns.lineplot(data = df_temp_EN, x= 'generation', y='max', color="red", label='Max', ax = ax[0])
sns.lineplot(data = df_temp_XG, x= 'generation', y='mean', color="blue", label='Mean', ax = ax[1])
sns.lineplot(data = df_temp_XG, x= 'generation', y='max', color="red", label='Max', ax = ax[1])
ax[0].set(ylim=(0.7, 0.85))
ax[1].set(ylim=(0.7, 0.85))
ax[0].xaxis.set_major_locator(MaxNLocator(integer=True))
ax[1].xaxis.set_major_locator(MaxNLocator(integer=True))
plt.setp(ax[:], xlabel='Generation')
plt.setp(ax[:], ylabel='AUC')
plt.show()

# Clear objects
del df_temp_EN, df_temp_XG, fig, df_vis, ax

# EN scores
df_temp_EN = df_ENet_AUC

# XG scores
df_temp_XG = df_xgb_AUC

# Plot evaluation score
fig, ax = plt.subplots(1, 2, figsize=(16,6))
fig.suptitle("Distribution of Feature Size Per Generation", fontsize=16)    
ax[0].set_title("ELasticNet")
ax[1].set_title("XGBOOST")
sns.boxplot(data = df_temp_EN, x= 'generation', y='feature_size', color="blue", ax = ax[0])
sns.boxplot(data = df_temp_XG, x= 'generation', y='feature_size', color="red", ax = ax[1])
ax[0].set(ylim=(0, 369))
ax[1].set(ylim=(0, 369))
plt.setp(ax[:], xlabel='Generation')
plt.setp(ax[:], ylabel='Number of Features')
plt.show()

# Clear objects
del df_temp_EN, df_temp_XG, fig, ax

# Summarise EN scores
df_temp_EN = df_ENet_AUC.groupby('generation')['similarity_features'].agg(['mean']).reset_index()
df_temp_EN['model'] = 'ElasticNet'

# Summarise XG scores
df_temp_XG = df_xgb_AUC.groupby('generation')['similarity_features'].agg(['mean', 'max']).reset_index()
df_temp_XG['model'] = 'XGBOOST'

# Combine Dataframes
df_vis = pd.concat([df_temp_EN, df_temp_XG])

# Plot evaluation score
fig, ax = plt.subplots(1, 2, figsize=(16,6))
fig.suptitle("Average Similarity Between Candidate Features and Best Solution's Per Generation", fontsize=16)    
ax[0].set_title("ELasticNet")
ax[1].set_title("XGBOOST")
sns.lineplot(data = df_temp_EN, x= 'generation', y='mean', color="blue", label='Mean', ax = ax[0])
sns.lineplot(data = df_temp_XG, x= 'generation', y='mean', color="blue", label='Mean', ax = ax[1])
ax[0].set(ylim=(0, 1))
ax[1].set(ylim=(0, 1))
ax[0].xaxis.set_major_locator(MaxNLocator(integer=True))
ax[1].xaxis.set_major_locator(MaxNLocator(integer=True))
plt.setp(ax[:], xlabel='Generation')
plt.setp(ax[:], ylabel='Similarity')
plt.show()

# Clear objects
del df_temp_EN, df_temp_XG, fig, df_vis, ax

# Summarise EN scores
df_temp_EN = df_ENet_AUC.groupby('generation')['similarity_hyperparameters'].agg(['mean']).reset_index()
df_temp_EN['model'] = 'ElasticNet'

# Summarise XG scores
df_temp_XG = df_xgb_AUC.groupby('generation')['similarity_hyperparameters'].agg(['mean', 'max']).reset_index()
df_temp_XG['model'] = 'XGBOOST'

# Combine Dataframes
df_vis = pd.concat([df_temp_EN, df_temp_XG])

# Plot evaluation score
fig, ax = plt.subplots(1, 2, figsize=(16,6))
fig.suptitle("Average Similarity Between Candidate Hyperparameters and Best Candidate Per Generation", fontsize=16)    
ax[0].set_title("ELasticNet")
ax[1].set_title("XGBOOST")
sns.lineplot(data = df_temp_EN, x= 'generation', y='mean', color="blue", ax = ax[0])
sns.lineplot(data = df_temp_XG, x= 'generation', y='mean', color="blue", ax = ax[1])
ax[0].set(ylim=(0, 1))
ax[1].set(ylim=(0, 1))
ax[0].xaxis.set_major_locator(MaxNLocator(integer=True))
ax[1].xaxis.set_major_locator(MaxNLocator(integer=True))
plt.setp(ax[:], xlabel='Generation')
plt.setp(ax[:], ylabel='Similarity')
plt.show()

# Clear objects
del df_temp_EN, df_temp_XG, fig, df_vis, ax

"""Model Evaluation
We can now use the best model found by the GA and use this to predict against our validation dataset, the output below shows how the model performs on the training set in CV and the validation set.
"""

# Extract best solution
df_best_en = df_ENet_AUC[df_ENet_AUC.fitness_score == max(df_ENet_AUC.fitness_score)]

# Extract features
l_best_features_en = (df_best_en.features.tolist())[0]

# Extract the hyperparameters
l_best_hyperparms_en = (df_best_en.hyperparameters.tolist())[0]
n_hyperparams_en = len(l_best_hyperparms_en['name'])
hyperparameters_en = {l_best_hyperparms_en['name'][0]:l_best_hyperparms_en['value'][0]}
if n_hyperparams_en > 1:
    for i in range(n_hyperparams_en):
        tempparameters = {l_best_hyperparms_en['name'][i]:l_best_hyperparms_en['value'][i]}
        hyperparameters_en = {**hyperparameters_en, **tempparameters}

# Create model object
model_en = ElasticNet()

# Set Hyperparameters
model_en.set_params(**hyperparameters_en)

# Fit model
model_en.fit(df_train.iloc[:,l_best_features_en], df_train.TARGET)

# Predict on validation
y_pred_en = model_en.predict(df_validation.iloc[:,l_best_features_en])

# XGBOOST 
# Extract best solution
df_best_xg = df_xgb_AUC[df_xgb_AUC.fitness_score == max(df_xgb_AUC.fitness_score)]

# Extract features
l_best_features_xg = (df_best_xg.features.tolist())[0]

# Extract the hyperparameters
l_best_hyperparms_xg = (df_best_xg.hyperparameters.tolist())[0]
n_hyperparams_xg = len(l_best_hyperparms_xg['name'])
hyperparameters_xg = {l_best_hyperparms_xg['name'][0]:l_best_hyperparms_xg['value'][0]}
if n_hyperparams_xg > 1:
    for i in range(n_hyperparams_xg):
        tempparameters = {l_best_hyperparms_xg['name'][i]:l_best_hyperparms_xg['value'][i]}
        hyperparameters_xg = {**hyperparameters_xg, **tempparameters}

# Create model object
model_xg = XGBClassifier(scale_pos_weight = 25)

# Set Hyperparameters
model_xg.set_params(**hyperparameters_xg)

# Fit model
model_xg.fit(df_train.iloc[:,l_best_features_xg], df_train.TARGET)

# Predict on validation
y_pred_temp = ((model_xg.predict_proba(df_validation.iloc[:,l_best_features_xg])).tolist())
y_pred_xg = []
for i in range(len(df_validation)):
    y_pred_xg.append(y_pred_temp[i][1])

# Evaluation scores
print('ElasticNET')
print('Train Set AUC:', round((df_best_en.evaluation_score.tolist())[0], 3))
print('Validation Set AUC:', round(metrics.roc_auc_score(df_validation.TARGET, y_pred_en), 3))
print(' ')

# Evaluation scores
print('XGBOOST')
print('Train Set AUC:', round((df_best_xg.evaluation_score.tolist())[0], 3))
print('Validation Set AUC:', round(metrics.roc_auc_score(df_validation.TARGET, y_pred_xg), 3))

"""Conclusion
To conclude, GA appears to be a useful tool to apply both feature selection and hyperparameter tuning. The main drawback found during this process is the computational commitment required, while my code can 100% be optimised it is a relatively significant time committment. Taking the execution point out of consideration for the moment the GA does typically drive the modelling solution in the right areas of the search space.

In practice I might be more tempted to use GA to generate sparse models with reasonable predictive power rather than to maximise a performance metric. I might explore this in another notebook.

It has been good practice playing with functions and creating a workflow for both machine learning models and for a hack implementation of a GA for hyperparameter tuning and feature selection.
"""
