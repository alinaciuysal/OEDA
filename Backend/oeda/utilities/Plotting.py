import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import matplotlib.pyplot as plt

def draw_box_plot(incoming_data_type_name, x_values, y_values, ts_name, folder_name, sample_size):
    # Create a figure instance
    fig = plt.figure(1, figsize=(9, 6))
    # Create an axes instance
    ax = fig.add_subplot(111)
    # Create the boxplot & format it
    format_box_plot(ax, y_values)
    ax.set_title('Boxplots of single-method process (SM) and 3-method process (3M), ' + str(sample_size) + " sample size")
    ax.set_ylabel(incoming_data_type_name)
    ax.set_xlabel("Type of process and number of optimizer iterations applied")
    # Custom x-axis labels for respective samples
    ax.set_xticklabels(x_values)
    # Remove top axes and right axes ticks
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()
    median_legend = mlines.Line2D([], [], color='green', marker='^', linestyle='None',
                                  markersize=5, label='Mean')
    mean_legend = mpatches.Patch(color='red', label='Median')
    plt.legend(handles=[median_legend, mean_legend])
    # plt.xticks(rotation=45)
    plot_path = './results/' + str(folder_name) + '/' + str(ts_name).lower() + '/comparison_' + str(incoming_data_type_name) + "_" + str(sample_size) + ".png"
    plt.savefig(plot_path, bbox_inches='tight', format='png')
    plt.close()


# http://blog.bharatbhole.com/creating-boxplots-with-matplotlib/
def format_box_plot(ax, y_values):
    bp = ax.boxplot(y_values, showmeans=True, showfliers=False)
    for median in bp['medians']:
        median.set_color('red')
    ## change the style of means and their fill
    for mean in bp['means']:
        mean.set_color('green')