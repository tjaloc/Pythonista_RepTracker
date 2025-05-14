import os
import pandas as pd
from datetime import datetime as dt

class RepTracker:
  def __init__(self, name, goal):
    self.name = name
    self.goal = goal
    self.year = dt.today().year
    self.cols = ['date', 'reps']
    self.df = pd.DataFrame(columns=self.cols)
    
    self.make_dir()
    self.read_data()
    
  def make_dir(self, dirname='csv'):
    if not os.path.exists(dirname):
      os.mkdir(dirname)
    
  def read_data(self):
    path = self.file_path
    if os.path.exists(path):
      self.df = pd.read_csv(path, usecols=self.cols, index_col=None)
    else:
      self.df = pd.DataFrame(columns=self.cols)
      
  def save(self):
    if self.df.empty:
      return
    self.df.to_csv(self.file_path, sep=',', columns=self.cols, index=False)
    
  def add(self, reps):
    now = dt.now()
    new_row = pd.DataFrame([[now, reps]], columns=self.cols)
    self.df = pd.concat([self.df, new_row], ignore_index=True)
    self.save()
    
  @property
  def file_path(self):
    return os.path.join('csv', f'{self.name}_{self.year}.csv')
    
  @property
  def sum(self):
    if self.df.empty:
      return 0
    return self.df['reps'].sum()
    
  @property
  def fraction(self):
    if self.df.empty:
      return 0
    return self.sum/self.goal
    
