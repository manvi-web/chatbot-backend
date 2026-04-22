import django_tables2 as tables
from django_tables2 import TemplateColumn

class NameTable(tables.Table):
        Packages = tables.Column()
        os = tables.Column(verbose_name="OS")
        Scheduler = tables.Column()
        Master = tables.Column()
        vcpu = tables.Column(verbose_name="vCPUs")
        Compute = tables.Column()
        MemoryinGB = tables.Column(verbose_name="Memory (GB)")
        MaxCompute = tables.Column(verbose_name="Max Compute")
        #ProcessingCostPerClusterPerHrinDollars = tables.Column(verbose_name="")
        StorageinGB = tables.Column(verbose_name="Storage (GB)")
        StorageCostPerHrinDollars = tables.Column(verbose_name="Storage Cost ($/Hr)")
        TotalCostPerClusterPerHrinDollars = tables.Column(verbose_name="Processing Cost ($/Hr)")
        ProcessingTimePerClusterPerTBinHrs = tables.Column(verbose_name="Processing Time (Hrs/TB)")
        TotalCostPerClusterPerTBinDollars = tables.Column(verbose_name="Total Cost ($/TB)")
        Action = tables.TemplateColumn(template_name='ClusterExpressLaunchButton.html')
        
class SingleNodeNameTable(tables.Table):
        Packages = tables.Column()
        os = tables.Column(verbose_name="OS")
        #Machine = tables.Column()
        id = tables.Column(visible=False)
        #os = tables.Column()
        #Packages = tables.Column()
        vcpu = tables.Column(verbose_name="vCPUs")
        Machine = tables.Column()
        MemoryinGB = tables.Column(verbose_name="Memory (GB)")
        StorageCapacityinGB = tables.Column(verbose_name="Storage Capacity (GB)")
        StorageCostPerHrinDollars = tables.Column(verbose_name="Storage Cost ($/Hr)")
        TotalCostPerHrinDollars = tables.Column(verbose_name="Processing Cost ($/Hr) ")
        ProcessingTimePerTBinHrs = tables.Column(verbose_name="Processing Time (Hrs/TB)")
        TotalCostPerTBinDollars = tables.Column(verbose_name="Total Cost ($/TB)")
        Action = tables.TemplateColumn(template_name='SingleNodeExpressLaunchButton.html')



class ResourcesTable(tables.Table):
        StackName = tables.Column()
        LaunchTime = tables.Column()
        ResourceType = tables.Column()
        Connect = tables.TemplateColumn(verbose_name=u'',template_name='ConnectResourceButton.html')
        Delete = tables.TemplateColumn(verbose_name=u'',template_name='DeleteResourceButton.html')
        
