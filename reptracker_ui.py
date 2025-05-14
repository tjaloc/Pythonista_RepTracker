import json
import math
import ui
import re

from colorsys import hls_to_rgb, rgb_to_hls
from csv_handler import RepTracker

SETTINGS_FILE = 'challenges.json'

def load_settings():
  try:
    with open(SETTINGS_FILE, 'r') as f:
      return json.load(f)
  except FileNotFoundError:
    return []

def save_settings(data:dict):
  with open(SETTINGS_FILE, 'w') as f:
    json.dump(data, f, indent=2)


# color tools
def adjust_color(color, lightness=0.7, saturation=0.125):
    """Adjust color using HSL space"""
    if isinstance(color, str):
        color = ui.parse_color(color)
    h, l, s = rgb_to_hls(*color[:3])
    return hls_to_rgb(h, max(0, min(1, lightness)), max(0, min(1, s * saturation)))

def apply_color_range(goals):
  hue = lambda x: (x/len(goals))
  clr = [hls_to_rgb(x/len(goals), 0.4, 0.8) for x in range(len(goals))]
  for ex, c in zip(goals, clr):
    ex['color'] = c

# GUI
class DonutChart(ui.View):
  def __init__(self, sum=0, goal=1, color='black', *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.sum = sum
    self.goal = goal
    self.progress_color = color
    self.bg_color = '#E0E0E0'
    self.goal_color = '#D0D0D0'
    self.line_width = max(5, self.width // 7)
    self.label = ui.Label(
        alignment=ui.ALIGN_CENTER,
        number_of_lines=0
    )
    self.add_subview(self.label)

  def layout(self):
    margin = self.line_width + 5
    self.label.frame = self.bounds.inset(margin, margin)
    self.update_label()

  def update_label(self, current=None):
    if current is not None:
      self.sum = current

    lbl_text = f'{self.sum:,}\n—\n{self.goal:,}'
    self.label.text = lbl_text.replace(',','.')
    max_size = min(self.label.width, self.height) * 0.1
    self.label.font = ('<system-bold>', max_size)
    self.set_needs_display()

  def draw(self):
    # Zeichenbereich berechnen
    rect = self.bounds.inset(self.line_width/2, self.line_width/2)
    radius = min(rect.width, rect.height)/2.5
    center = ui.Point(self.width/2, self.height/2)

    # progress
    progress = min(self.sum / self.goal, 1.0)
    start_angle = -math.pi/2
    end_angle = start_angle + 2 * math.pi * progress

    # Startpunkt berechnen
    start_x = center.x + radius * math.cos(start_angle)
    start_y = center.y + radius * math.sin(start_angle)

    # Hintergrundkreis
    bg_path = ui.Path()
    bg_path.move_to(start_x, start_y)
    bg_path.line_width = self.line_width
    bg_path.add_arc(
      center.x, center.y, radius,
      -math.pi/2, 3 * math.pi/2)
    ui.set_color(self.goal_color)
    bg_path.stroke()

    if self.goal == 0 or self.sum == 0:
      return

    # Fortschrittskreis
    progress_path = ui.Path()
    progress_path.line_width = self.line_width
    progress_path.move_to(start_x, start_y)
    progress_path.add_arc(
        center.x, center.y, radius,
        start_angle, end_angle,
        True
    )
    ui.set_color(self.progress_color)
    progress_path.stroke()

class FitnessTracker(ui.View):
  def __init__(self, *args, **kwargs):
    super().__init__(name='RepTracker', *args, **kwargs)
    self.background_color = '#e0e0e0'
    self.aspectratio = 4/5.5
    
    # UI Elemente erstellen
    self.get_goals()
    if self.shortcuts:
      self.setup()
      self.create_workout_views()
    self.add_settings_btn()
    
    self.present('full_screen')
    if not self.shortcuts:
      self.show_settings()
    
  def get_goals(self):
    self.shortcuts = load_settings()
    
  def setup(self):
    # set dimensions
    w, h = ui.get_screen_size()
    self.frame = (0,0,w,h -100)
    self.cols = 2 
    if len(self.shortcuts) > 6:
      self.cols = 3
    self.rows = max(1, math.ceil(len(self.shortcuts)/self.cols))
    self.chart_size = min(self.width/self.cols, self.height/(self.rows/self.aspectratio))
    
    # create colors
    apply_color_range(self.shortcuts)
    
    # elem dicts to target objects by name/key
    self.entries = {}
    self.buttons = {}
    self.tracker = {}
    self.charts = {}

  def add_settings_btn(self):
    btn = ui.Button(
      name='settings',
      frame=(self.width-35, 5, 32, 32),
      image=ui.Image('iob:ios7_cog_32'),
      tint_color='white',
      action=self.action_settings
    )
    self.add_subview(btn)
    
  def show_settings(self):
    settings_view = Settings(self, frame=(0, 0, 400, 600))
    settings_view.present('popover')

  def action_settings(self, sender):
    self.show_settings()

  def reload_data(self):
    # reload settings
    self.get_goals()

    # remove ui elements
    for sv in self.subviews:
      self.remove_subview(sv)
      
    self.setup()
    self.create_workout_views()
    self.add_settings_btn()


  def create_workout_views(self):
    if not self.shortcuts:
      self.add_settings_btn()
      return
      
    gap_w = (self.width - (self.cols * self.chart_size)) /3
    for i, exercise in enumerate(self.shortcuts):
      ex_name = exercise['title']
      row, col = divmod(i, self.cols)
      w = self.chart_size
      h = w / self.aspectratio
      x = col * (w + gap_w) + gap_w
      y = row * h

      # Container View
      cont_w = self.width/self.cols
      cont_h = cont_w / self.aspectratio
      container = ui.View(
          name=exercise['title'],
          frame=(x, y, cont_w, cont_h),
          background_color='#e0e0e0'
      )

      # Donut Chart
      tracker = RepTracker(name=ex_name, goal=exercise['goal'])
      self.tracker[exercise['title']] = tracker
      
      chart_x = (cont_w - self.chart_size)/2
      chart = DonutChart(
          sum=tracker.sum,
          goal=tracker.goal,
          color=exercise.get('color', (0.75, 0.06, 0.6)),
          frame=(chart_x, 15, self.chart_size, self.chart_size)
      )
      chart.goal_color = adjust_color(exercise.get('color',(1,1,1)))

      # Exercise Label
      lbl = ui.Label(
          text=ex_name.title(),
          frame=(0, 5, cont_w, 20),
          font=('<System-Bold>', 12),
          alignment=ui.ALIGN_CENTER
      )

      # Button
      btn = ui.Button(
          #title='+',
          frame=(cont_w -40, h - 32, 32, 32),
          corner_radius=16,
          bg_color=exercise.get('color',(0.75, 0.06, 0.6)),
          image=ui.Image('iob:plus_circled_32'),
          tint_color='white',
          action=self.button_action
      )
      btn.name = exercise['title']

      # Entry
      ent = ui.TextField(
        title=ex_name,
        name=ex_name,
        alignment=1,
        keyboard_type=ui.KEYBOARD_NUMBERS,
        frame=(btn.width, h - 32, cont_w -(2.3 * btn.width), 32),
        corner_radius=btn.width/2,
        )

      container.add_subview(chart)
      container.add_subview(lbl)
      container.add_subview(ent)
      container.add_subview(btn)
      self.add_subview(container)

      self.entries[ex_name] = ent
      self.buttons[ex_name] = btn
      self.charts[ex_name] = chart

  def button_action(self, sender):
    if not self.entries[sender.name].text:
      return

    reps = int(self.entries[sender.name].text)
    tracker = self.tracker[sender.name]
    tracker.add(reps)
    self.charts[sender.name].update_label(
      tracker.sum)
    self.entries[sender.name].text = ''


class Settings(ui.View):
  def __init__(self, main_view, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.name = 'Challenges'
    self.main_view = main_view
    self.background_color = '#e0e0e0'
    self.data = load_settings()
    self.goal_entries = {}
    self.create_ui()
    self.alpha = .85

  def create_ui(self):
    y = 10
    if self.data:
      # Bestehende Übungen
      y = 50
      for i, item in enumerate(self.data):
        row = self.create_setting_row(item, y, i)
        self.add_subview(row)
        y += 50

    # Neue Übung hinzufügen
    y += 20
    add_label = ui.Label(
        frame=(20, y, self.width-40, 30),
        text='Add a Challenge:',
        font=('<system>', 14)
    )
    self.add_subview(add_label)
    y += 35

    self.new_title = ui.TextField(
        frame=(20, y, 200, 32),
        placeholder='Exercise',
        bordered=True
    )

    self.new_goal = ui.TextField(
        frame=(230, y, 90, 32),
        placeholder='Goal',
        alignment=2,
        keyboard_type=ui.KEYBOARD_NUMBERS,
        bordered=True
    )

    add_btn = ui.Button(
        name='Hinzufügen',
        frame=(360, y, 32, 32),
        action=self.add_new_item,
        bg_color='#72c135',
        tint_color='white',
        image=ui.Image('iow:plus_round_32'),
        corner_radius=9,
        content_mode=ui.CONTENT_SCALE_ASPECT_FIT
    )
    
    self.add_subview(self.new_title)
    self.add_subview(self.new_goal)
    self.add_subview(add_btn)

  def create_setting_row(self, item, y, index):
    row = ui.View(frame=(0, y, self.width, 40))

    title = ui.Label(
        frame=(20, 0, 140, 40),
        text=item['title'],
        font=('<system>', 14)
    )

    goal_field = ui.TextField(
        frame=(170, 5, 80, 32),
        text=str(item['goal']),
        alignment=2,
        keyboard_type=ui.KEYBOARD_NUMBER_PAD,
        bordered=True
    )
    goal_field.name = f'goal_{index}'
    self.goal_entries[f'goal_{index}'] = goal_field

    update_btn = ui.Button(
        name='save',
        frame=(290, 5, 32, 32),
        action=self.update_item,
        image=ui.Image('iow:checkmark_round_32'),
        corner_radius=9,
        bg_color='#39afc1',
        tint_color='white',
        flex='W'
    )
    update_btn.name = str(index)

    delete_btn = ui.Button(
        name='delete',
        frame=(360, 5, 32, 32),
        action=self.delete_item,
        image=ui.Image('iow:trash_a_32'),
        bg_color='#c15a35',
        corner_radius=9,
        tint_color='white'
    )
    delete_btn.name = str(index)

    row.add_subview(title)
    row.add_subview(goal_field)
    row.add_subview(update_btn)
    row.add_subview(delete_btn)
    return row

  def update_item(self, sender):
    index = int(sender.name)
    
    try:
      new_goal = int(self.goal_entries[f'goal_{index}'].text)
    except ValueError:
      # ignore if field is empty
      return
      
    self.data[index]['goal'] = new_goal
    save_settings(self.data)
    self.main_view.reload_data()
    self.close()

  def delete_item(self, sender):
    index = int(sender.name)
    del self.data[index]
    save_settings(self.data)
    self.main_view.reload_data()
    self.close()
    
  def contains_word(self, textentry):
    return bool(re.match(r'\w+', textentry))

  def add_new_item(self, sender):
    # Only add new item if title and goal exist
    new_title = self.new_title.text.strip()
    if not self.contains_word(new_title):
      return
      
    try:
      new_goal = int(self.new_goal.text)
    except ValueError:
      return
    
    new_item = {
        'title':new_title,
        'goal': new_goal
    }
    self.data.append(new_item)
    save_settings(self.data)
    self.main_view.reload_data()
    self.close()

if __name__ == '__main__':
  w, h = ui.get_screen_size()
  v = FitnessTracker()
  
