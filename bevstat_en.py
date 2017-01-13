
import numpy as np
from os import path
from bokeh.io import curdoc
from bokeh.layouts import row, column, widgetbox, layout
from bokeh.models import ColumnDataSource, formatters, BoxAnnotation, BoxSelectTool, HoverTool, Span, Label, Button
from bokeh.models.widgets import Slider, PreText, RadioGroup
from bokeh.plotting import figure
from functools import lru_cache


data_dir = "pop_data"
additional_stats = dict()
additional_stats_source = dict()
age_data = dict()
display_stats = dict()

#load data from csvs, actual population counts 1971-2015 and scenarios 2016-2045
for data_time in ("historical", "low_prediction", "reference_prediction", "high_prediction"):
    age_data[data_time] = dict()
    for data_demographic in ("m_ch","m_au","f_ch","f_au"):
        age_data[data_time][data_demographic] = np.loadtxt(path.join(data_dir,
                                                                      data_time +
                                                                      "_" +
                                                                      data_demographic +
                                                                      ".csv"),
                                                                      dtype=int)
        #invert all data for the female portion (negative barplots for all female values):
        if data_demographic.startswith("f"):
            age_data[data_time][data_demographic] *= -1

#load migration and birth stats, also with scenarios
for key in ("historical_ch","historical_au","low_ch","low_au","ref_ch","ref_au","high_ch","high_au"):
    additional_stats[key] = np.rot90(np.fliplr(np.loadtxt(path.join(data_dir,key + ".stats"), dtype=int)))
    additional_stats[key][2] *= -1
    additional_stats[key][4] *= -1


age_groups = [k for k in range(101)]
x_scatter = np.zeros(101)



class Bevstat():
    def __init__(self, age_data, additional_stats, first_recorded_year):
        self.age_data = age_data
        self.additional_stats = additional_stats
        self.first_recorded_year = first_recorded_year
        self.labor_age_min = 18
        self.labor_age_max = 67
        self.radio_active = 1
        self.age_groups = [group for group in range(101)]
        self.age_data_source = dict()
        self.display_stats = dict()
        self.additional_stats_source = dict()

        self.underage_box = BoxAnnotation(top=self.labor_age_min, fill_alpha=0.15, fill_color='red')
        self.laborage_box = BoxAnnotation(bottom=self.labor_age_min, top=self.labor_age_max, fill_alpha=0.15, fill_color='green')
        self.retired_box = BoxAnnotation(bottom=self.labor_age_max, fill_alpha=0.15, fill_color='red')

        self.births_box = BoxAnnotation(left=first_recorded_year,
                                        right=first_recorded_year + 1,
                                        line_width = 0.3,
                                        line_color = "black",
                                        line_alpha = 1,
                                        fill_alpha=0.2,
                                        fill_color='yellow')

        self.migration_box = BoxAnnotation(left=first_recorded_year,
                                           right=first_recorded_year + 1,
                                           line_width=0.3,
                                           line_color="black",
                                           line_alpha=1,
                                           fill_alpha=0.2,
                                           fill_color='yellow')

        self.dependency_ratio_textfield = PreText(text="", width=500)
        self.total_population_textfield = PreText(text="", width=500)

        self.display_stats["ch"] = np.hstack((self.additional_stats["historical_ch"], self.additional_stats["ref_ch"]))
        self.display_stats["au"] = np.hstack((self.additional_stats["historical_au"], self.additional_stats["ref_au"]))

        for data_demographic in ("m_ch", "m_au", "f_ch", "f_au"):
            self.age_data_source[data_demographic] = ColumnDataSource(
                data=dict(y=self.age_groups, display=self.age_data["historical"][data_demographic][0]))

        self.historical_years = len(self.age_data["historical"]["m_ch"])
        self.predicted_years = len(self.age_data["reference_prediction"]["m_ch"])

        self.offset_slider = Slider(title="", value=0, start=0, end=self.historical_years + self.predicted_years -1,
                                    step=1, sizing_mode="scale_height", orientation="horizontal")
        #changing icons on the fly diesnt seem to work
        #Bokeh Icons are removed with 0.12.4
        #self.icon_arrow = Icon(icon_name="arrow-circle-up")
        self.animate_button = Button(label="Animation", width=70)
        self.animate_button.on_click(self.animation_button_click)

        for origin in ("ch", "au"):
            self.additional_stats_source[origin] = ColumnDataSource(data=dict(years=self.display_stats[origin][0] + 0.25,
                                                                         births=self.display_stats[origin][1],
                                                                         deaths=self.display_stats[origin][2],
                                                                         immigration=self.display_stats[origin][3],
                                                                         migration=self.display_stats[origin][4]))

    def update_stat_plots(self, radio_active):
        self.radio_active = radio_active

        for num, stat in enumerate(['births', 'deaths', 'immigration', 'migration'], 1):
            if self.radio_active == 0:
                self.additional_stats_source['ch'].data[stat] = np.hstack(
                    (self.additional_stats["historical_ch"][num], self.additional_stats["low_ch"][num]))
                self.additional_stats_source['au'].data[stat] = np.hstack(
                    (self.additional_stats["historical_au"][num], self.additional_stats["low_au"][num]))
            if self.radio_active == 1:
                self.additional_stats_source['ch'].data[stat] = np.hstack(
                    (self.additional_stats["historical_ch"][num], self.additional_stats["ref_ch"][num]))
                self.additional_stats_source['au'].data[stat] = np.hstack(
                    (self.additional_stats["historical_au"][num], self.additional_stats["ref_au"][num]))
            if self.radio_active == 2:
                self.additional_stats_source['ch'].data[stat] = np.hstack(
                    (self.additional_stats["historical_ch"][num], self.additional_stats["high_ch"][num]))
                self.additional_stats_source['au'].data[stat] = np.hstack(
                    (self.additional_stats["historical_au"][num], self.additional_stats["high_au"][num]))

        self.update_data(self.offset_slider.value)

    def animation_button_click(self):
        if self.animate_button.label == "Animation":
            self.animate_button.label = "Stop"
            curdoc().add_periodic_callback(self.button_animation, 200)
        else:
            self.animate_button.label = "Animation"
            curdoc().remove_periodic_callback(self.button_animation)

    def button_animation(self):
        if self.offset_slider.value < self.historical_years + self.predicted_years - 1 :
            self.animate_button.label = "Stop"
            self.offset_slider.value += 1
        else:
            self.animate_button.label = "Animation"
            curdoc().remove_periodic_callback(self.button_animation)
            self.offset_slider.value = 0
        self.update_data(self.offset_slider.value)


    def update_dependency_box(self, labor_age_min, labor_age_max):
        self.labor_age_min = labor_age_min
        self.labor_age_max = labor_age_max

        self.underage_box.update(top=self.labor_age_min)
        self.laborage_box.update(bottom=self.labor_age_min, top=self.labor_age_max)
        self.retired_box.update(bottom=self.labor_age_max)
        dependency_tuple = self.prepare_dependency_text(self.labor_age_min,
                                                        self.labor_age_max,
                                                        self.offset_slider.value,
                                                        self.radio_active)
        self.update_dependency_text(*dependency_tuple)

    @lru_cache(maxsize=256)
    def prepare_dependency_text(self, labor_age_min, labor_age_max, slider_value, radio_active):
        display_data_total = self.age_data_source['m_ch'].data['display'] \
                             + (-1 * self.age_data_source['f_ch'].data['display'])
        dependency_ratio_minor = (sum(display_data_total[0:labor_age_min])) / sum(display_data_total[labor_age_min:])
        dependency_ratio_major = (sum(display_data_total[labor_age_max:])) / sum(display_data_total[:labor_age_max])
        dependency_ratio = dependency_ratio_minor + dependency_ratio_major
        return dependency_ratio, dependency_ratio_minor, dependency_ratio_major

    def update_dependency_text(self, dep, dep_min, dep_maj):
        self.dependency_ratio_textfield.update(
            text="Dependency ratio: {dependency_ratio:.2f} \n"
                 "\t- Underage: {dependency_ratio_minor:.2f} with working age: {working_age}\n"
                 "\t- Retired: {dependency_ratio_major:.2f} with retirement age: {retirement_age}".format(
                retirement_age=self.labor_age_max,
                working_age=self.labor_age_min,
                dependency_ratio=dep,
                dependency_ratio_minor = dep_min,
                dependency_ratio_major = dep_maj))

    @lru_cache(maxsize=256)
    def prepare_population_text(self, slider_value, radio_active):
        return sum(self.age_data_source['m_ch'].data['display']),\
               sum(self.age_data_source['f_ch'].data['display']) * -1,\
               sum(self.age_data_source['m_au'].data['display']),\
               sum(self.age_data_source['f_au'].data['display']) * -1

    def update_population_text(self, m_ch_sum, f_ch_sum, m_au_sum, f_au_sum):
        self.total_population_textfield.update(text="Total population: {total_pop:,}\n"
                                                    "\t- Male: {total_pop_m:,}\n"
                                                    "\t\t- Swiss: {total_pop_m_ch:,}\n"
                                                    "\t\t- Foreign: {total_pop_m_au:,}\n"
                                                    "\t- Female: {total_pop_f:,}\n"
                                                    "\t\t- Swiss: {total_pop_f_ch:,}\n"
                                                    "\t\t- Foreign: {total_pop_f_au:,}".format(
            total_pop=m_ch_sum + f_ch_sum,
            total_pop_m=m_ch_sum,
            total_pop_m_ch=m_ch_sum - m_au_sum,
            total_pop_m_au=m_au_sum,
            total_pop_f=f_ch_sum,
            total_pop_f_ch=f_ch_sum - f_au_sum,
            total_pop_f_au=f_au_sum))

    def get_new_display_data(self, slider_value, radio_active):
        if slider_value < self.historical_years:
            return self.age_data['historical']['m_ch'][slider_value],\
                   self.age_data['historical']['m_au'][slider_value],\
                   self.age_data['historical']['f_ch'][slider_value],\
                   self.age_data['historical']['f_au'][slider_value]

        elif slider_value >= self.historical_years and self.radio_active == 0:
            return self.age_data['low_prediction']['m_ch'][slider_value - self.historical_years],\
                   self.age_data['low_prediction']['m_au'][slider_value - self.historical_years],\
                   self.age_data['low_prediction']['f_ch'][slider_value - self.historical_years],\
                   self.age_data['low_prediction']['f_au'][slider_value - self.historical_years]

        elif slider_value >= self.historical_years and self.radio_active == 1:
            return self.age_data['reference_prediction']['m_ch'][slider_value - self.historical_years],\
                   self.age_data['reference_prediction']['m_au'][slider_value - self.historical_years],\
                   self.age_data['reference_prediction']['f_ch'][slider_value - self.historical_years],\
                   self.age_data['reference_prediction']['f_au'][slider_value - self.historical_years]

        elif slider_value >= self.historical_years and self.radio_active == 2:
            return self.age_data['high_prediction']['m_ch'][slider_value - self.historical_years],\
                   self.age_data['high_prediction']['m_au'][slider_value - self.historical_years],\
                   self.age_data['high_prediction']['f_ch'][slider_value - self.historical_years],\
                   self.age_data['high_prediction']['f_au'][slider_value - self.historical_years]


    def update_current_year_box(self, slider_value):
        for box in (self.births_box, self.migration_box):
            box.update(left=self.first_recorded_year + slider_value,
                       right=self.first_recorded_year + slider_value + 1)


    def update_data(self, slider_value):
        self.age_data_source['m_ch'].data['display'], \
        self.age_data_source['m_au'].data['display'], \
        self.age_data_source['f_ch'].data['display'], \
        self.age_data_source['f_au'].data['display'] = self.get_new_display_data(self.offset_slider.value, self.radio_active)
        poptext_tuple = self.prepare_population_text(self.offset_slider.value, self.radio_active)
        self.update_population_text(*poptext_tuple)
        deptext_tuple = self.prepare_dependency_text(self.labor_age_min,
                                                 self.labor_age_max,
                                                 self.offset_slider.value,
                                                 self.radio_active)
        self.update_dependency_text(*deptext_tuple)
        self.update_current_year_box(self.offset_slider.value)
        plot.title.text = "Total resident population (Switzerland): {}".format(str(self.first_recorded_year + self.offset_slider.value))




bevstat = Bevstat(age_data, additional_stats, 1971)

###############################################################################################
###############################################################################################

hovertool_births = HoverTool(tooltips=[("Birth surplus", "@y"),("Year","@x")])
hovertool_migration = HoverTool(tooltips=[("Net migration", "@y"),("Year","@x")])

plot = figure(plot_height=400, plot_width=600, title="Total resident population (Switzerland): 2010",
              tools=["save", "box_select"],
              x_range=[-85000, 85000],
              y_range=[0, 101])

plot_birth = figure(plot_height=400, plot_width=600, title="Birth surplus",
              tools=[hovertool_births],
              x_range=[bevstat.display_stats["ch"][0][0],bevstat.display_stats["ch"][0][-1]],
              y_range=[-100000, 100000])

plot_migration = figure(plot_height=400, plot_width=600, title="Net migration",
              tools=[hovertool_migration],
              x_range=[bevstat.display_stats["ch"][0][0],bevstat.display_stats["ch"][0][-1]],
              y_range=[-180000, 180000])


for stat_type in ("births","deaths"):
    for key in bevstat.additional_stats_source:
        vbar_color = "blue" if "ch" in key else "red"
        plot_birth.vbar(x='years',
                        top=stat_type,
                        source=bevstat.additional_stats_source[key],
                        bottom=0,
                        width=0.5,
                        alpha=0.1,
                        color=vbar_color)


hovertool_births.renderers.append(plot_birth.line(x=np.array(bevstat.display_stats["ch"][0]),
                     y=bevstat.display_stats["ch"][1]+bevstat.display_stats["ch"][2],
                     line_width=4,
                     color="blue",
                     legend="Birth surplus (Swiss)"))

hovertool_births.renderers.append(plot_birth.line(x=np.array(bevstat.display_stats["au"][0]),
                     y=bevstat.display_stats["au"][1]+bevstat.display_stats["au"][2],
                     line_width=4,
                     color="red",
                     legend="Birth surplus (Foreign)"))


for stat_type in ("migration","immigration"):
    for key in bevstat.additional_stats_source:
        vbar_color = "blue" if "ch" in key else "red"
        plot_migration.vbar(x='years',
                        top=stat_type,
                        source=bevstat.additional_stats_source[key],
                        bottom=0,
                        width=0.5,
                        alpha=0.1,
                        color=vbar_color)


hovertool_migration.renderers.append(plot_migration.line(x=np.array(bevstat.display_stats["ch"][0]),
                     y=bevstat.display_stats["ch"][3]+bevstat.display_stats["ch"][4],
                     line_width=4,
                     color="blue",
                     legend="Net migration (Swiss)"))

hovertool_migration.renderers.append(plot_migration.line(x=np.array(bevstat.display_stats["ch"][0]),
                     y=bevstat.display_stats["au"][3]+bevstat.display_stats["au"][4],
                     line_width=4,
                     color="red",
                     legend="Net migration (Foreign)"))

#only scatterplots can be selectec with boxselect
#invisible scatter along x=0
scatter = plot.scatter(x=x_scatter, y=age_groups, size=0)

plot.legend.location = "top_right"
plot.legend.background_fill_color = "white"
plot.legend.background_fill_alpha = 0.8
plot.legend.border_line_color = "black"
plot.legend.border_line_width = 2

plot_birth.legend.location = "bottom_left"
plot_migration.legend.location = "bottom_left"


#dotted line separating male / female
m_f_separator = Span(location=0, dimension='height', line_dash='dashed', line_color='black', line_width=1)

annotation_female = Label(x=85, y=35, x_units='screen', y_units='screen',
                 text='Weiblich', render_mode='css',
                 border_line_color='black', border_line_alpha=0.4,
                 background_fill_color='white', background_fill_alpha=0.7)

annotation_male = Label(x=495, y=35, x_units='screen', y_units='screen',
                 text='Männlich', render_mode='css',
                 border_line_color='black', border_line_alpha=0.4,
                 background_fill_color='white', background_fill_alpha=0.7)

plot.yaxis.axis_label = "Age"
plot.xaxis.formatter = formatters.NumeralTickFormatter(format="(0,0)")

plot_birth.yaxis.axis_label = "deaths (-)  births (+)"
plot_birth.yaxis.formatter = formatters.PrintfTickFormatter(format="%d")
plot_birth.xgrid.minor_grid_line_alpha = 0.5

plot_migration.yaxis.axis_label = "emigration (-)  immigration (+)"
plot_migration.yaxis.formatter = formatters.PrintfTickFormatter(format="%d")
plot_migration.xgrid.minor_grid_line_alpha = 0.5

#throttling doesnt' work with bokeh server, massive CPU-spike when
#toying with slider

prediction_radio_group = RadioGroup(
        labels=["Prediction scenario: \"low\"", "Referencescenario", "Prediction scenario \"high\""], active=1)


plot.hbar(right='display', y='y', source=bevstat.age_data_source["m_ch"], height=0.5, line_width=3, line_alpha=0.4, color="blue", legend="Swiss")
plot.hbar(right='display', y='y', source=bevstat.age_data_source["m_au"], height=0.5, line_width=3, line_alpha=0.4, color="red", legend="Foreign")
plot.hbar(right='display', y='y', source=bevstat.age_data_source["f_ch"], height=0.5, line_width=3, line_alpha=0.4, color="blue")
plot.hbar(right='display', y='y', source=bevstat.age_data_source["f_au"], height=0.5, line_width=3, line_alpha=0.4, color="red")


offset_changed = lambda attr,old,new: bevstat.update_data(new)
bevstat.offset_slider.on_change('value', offset_changed)

radio_group_changed = lambda attr: bevstat.update_stat_plots(prediction_radio_group.active)
prediction_radio_group.on_click(radio_group_changed)

scatter_changed = lambda attr,old,new: bevstat.update_dependency_box(min(new['1d']['indices']),
                                                                     max(new['1d']['indices']))
scatter.data_source.on_change('selected', scatter_changed)

bevstat.update_dependency_text(*bevstat.prepare_dependency_text(bevstat.labor_age_min,
                                                               bevstat.labor_age_max,
                                                               0,
                                                               1))
bevstat.update_population_text(*bevstat.prepare_population_text(0, 1))

inputs = widgetbox(bevstat.dependency_ratio_textfield, bevstat.total_population_textfield, prediction_radio_group, width=600)

curdoc().add_root(column(row(plot, column(inputs,bevstat.offset_slider, bevstat.animate_button)),
                         row(plot_birth, plot_migration)))
curdoc().title = "Swiss resident population history"

for my_plot in [plot_birth, plot_migration]:
    my_plot.toolbar.logo = None

for my_layout in [bevstat.underage_box, bevstat.laborage_box, bevstat.retired_box, m_f_separator, annotation_male, annotation_female]:
    plot.add_layout(my_layout)

plot_birth.add_layout(bevstat.births_box)
plot_migration.add_layout(bevstat.migration_box)
