# ViewSeries.py
#
# This is a simple example to get familar with programming in Slicer.
#
# The list of patients is extracted from the DICOM database and displayed. When
# the user clicks on a patient, the studies corresponding the patient are
# listed. Clicking on a study populates the viewer, where one view is created
# for each series. The corresponding data is displayed in each viewer.
#
# Notes:
#     https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#load-dicom-files-into-the-scene-from-a-folder
#     https://github.com/pieper/CompareVolumes/blob/master/CompareVolumes.py 
#     https://github.com/Slicer/Slicer/blob/master/Modules/Scripted/DICOMPlugins/DICOMScalarVolumePlugin.py
#     https://github.com/QIICR/QuantitativeReporting/blob/87852c8460ed54de70e8c838f16ddf62da539546/DICOMPlugins/DICOMSegmentationPlugin.py#L699
#     https://github.com/SlicerRt/SlicerRT/blob/master/DicomRtImportExport/DicomRtImportExportPlugin.py 
#     https://discourse.slicer.org/t/windows-slicer-util-loadvolume-loads-wrong-volume/641 
#     https://discourse.slicer.org/t/importing-dicom-files-in-my-own-module-c/12455/4 
#     https://www.tutorialspoint.com/pyqt/pyqt_qlistwidget.htm
#     https://stackoverflow.com/questions/22571706/how-to-list-all-items-from-qlistwidget
#     https://stackoverflow.com/questions/23835847/how-to-remove-item-from-qlistwidget/23836142
#          # labelNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLVolumeArchetypeStorageNode") # 
        # labelNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationStorageNode")
        # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html
        # Export a segmentation to DICOM segmentation object 
        # labelNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
#
# To do:
#   Try with QListView instead of QListWidget?
#   Had to install Quantitative Reporting and SlicerRT extensions manually - how to load extensions automatically?
#
# Deepa Krishnaswamy
# Feburar 2021
# Brigham and Women's Hospital
################################################################################

from slicer.util import VTKObservationMixin
import numpy as np 

import os, json, xml.dom.minidom, string, glob, re, math
import vtk, qt, ctk, slicer
import logging
import CompareVolumes
import SimpleITK as sitk
import sitkUtils
import datetime
from slicer.ScriptedLoadableModule import *

from DICOMLib import DICOMPlugin

################################################################################

#
# ViewSeries
#

class ViewSeries(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "ViewSeries"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["Examples"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Deepa Krishnaswamy (BWH)"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """This is an example of a simple extension to view a set of series when a user clicks on a study.
                              The views layout contains the number of series that are in the study.
                              The studies are populated by entries in the DICOM database."""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
                                         and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1."""

    # # Add this test to the SelfTest module's list for discovery when the module
    # # is created.  Since this module may be discovered before SelfTests itself,
    # # create the list if it doesn't already exist.
    # try:
    #     slicer.selfTests
    # except AttributeError:
    #     slicer.selfTests = {}
    #
    # def runTest(self):
    #     return

    # Additional initialization step after application startup is complete
    # slicer.app.connect("startupCompleted()", registerSampleData)

#
# ViewSeriesWidget
#

class ViewSeriesWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False
    # added
    self.selectPatientName = ''
    self.selectStudyName = ''
    self.studyCollapsibleButton = None
    self.studyListWidget = None
    self.selectPatientNameIndex = None
    self.selectStudyNameIndex = None
    self.studyListWidgetNum = 0 # number of studies
    self.seriesListNum = 0 # number of series
    self.patientNames = None
    self.db = slicer.dicomDatabase
    self.patientList = None

  def selectPatient(self, item):

      """This is called when the user selects a patient name from the list.
         The corresponding study names are listed when a patient is selected.
      """

      print ('Patient ' + str(item.text()) + ' was clicked')
      self.selectPatientName = item.text()

      # Get the info from the slicer database
      # We need to find where the self.selectPatientName appears in the list of the patientNames
      patientList = list(self.db.patients())
      patientNames = []
      for patient in range(0,len(patientList)):
          studyList = self.db.studiesForPatient(patientList[patient])
          seriesList = self.db.seriesForStudy(studyList[0])
          fileList = self.db.filesForSeries(seriesList[0])
          patientNames.append(self.db.fileValue(fileList[0], "0010,0010"))
      self.patientNames = patientNames

      # Find which one it is in the list of patients
      index = patientNames.index(self.selectPatientName)
      patientNameClicked = patientNames[index]
      self.selectPatientNameIndex = index

      # Get the study names from the patient that was selected
      studyList = self.db.studiesForPatient(patientList[index])
      print ('studyList: ' + str(studyList)) # this is correct

      # First remove the previous studies from the list
      if not (self.studyListWidgetNum == 0): # if it's not equal to 0, remove items
          num_items = self.studyListWidget.count
          # get a list of the current items
          items = []
          for n in range(0,num_items):
              items.append(self.studyListWidget.item(n))
          # now remove these items from the list
          for item in items:
              self.studyListWidget.takeItem(self.studyListWidget.row(item))

      # Add the new study items in
      for study in studyList:
          self.studyListWidget.addItem(study)
      self.studyListWidgetNum = (self.studyListWidget).count
      print ('self.studyListWidgetNum: ' + str(self.studyListWidgetNum)) # this is correct, is 2

      # need to update the layout??

      # Select the study and then get the series and update the viewer.
      self.studyListWidget.itemClicked.connect(self.selectStudy)


  def selectStudy(self, item):

    """This is called when the user selects a study name from the list."""
    
    # do some cleanup first 
    self.removeObservers() # is this right??

    print ('Study ' + str(item.text()) + ' was clicked') # why is this printing out multiple times?
    self.selectStudyName = item.text()

    # Get the index of the study that was clicked
    index = self.patientNames.index(self.selectPatientName)
    studyNames = self.db.studiesForPatient(self.patientList[index])
    # print ('studyNames: ' + str(studyNames))

    index = studyNames.index(self.selectStudyName)
    studyNameClicked = studyNames[index]
    # Get the series names from the study that was selected
    seriesList = self.db.seriesForStudy(studyNames[index])
    print ('seriesList: ' + str(seriesList))
    self.seriesListNum = len(seriesList)
    print ('number of series: ' + str(self.seriesListNum))

    ## Set up the plugins
    # for the scalar volumes 
    DICOMScalarVolumePlugin = slicer.modules.dicomPlugins['DICOMScalarVolumePlugin']()
    # for the SEG label volumes 
    DICOMSegmentationPlugin = slicer.modules.dicomPlugins['DICOMSegmentationPlugin']()
    # for RTSTRUCT 
    DicomRtImportExportPlugin = slicer.modules.dicomPlugins['DicomRtImportExportPlugin']()
    
    ### Get the series that have SEG files ###

    self.segmentationNodesNum = 0
    self.segmentationNodesIndex = [] 
    self.volumeNodesNum = 0 
    self.volumeNodesIndex = [] 
    self.seriesDescription = [] 
    self.referencedSeriesUID = [] 
    
    for n in range(0,self.seriesListNum):
        
        # Get the list of files 
        fileList = self.db.filesForSeries(seriesList[n]) # should be n not 0 
        print ('fileList: ' + str(fileList))
        # Check the modality, want SEG 
        modality = self.db.fileValue(fileList[0], "0008,0060")
        print ('modality: ' + str(modality))
        
        # keep ones that have SEG - these are loaded 
        if (modality=="SEG"):
            loadables = DICOMSegmentationPlugin.examineFiles(fileList)
            self.segmentationNodesNum += 1 
            self.segmentationNodesIndex.append(n)
            self.referencedSeriesUID.append(loadables[0].referencedSeriesUID)
            
        elif (modality=="MR" or modality=="CT"):
            loadables = DICOMScalarVolumePlugin.examineFiles(fileList)
            self.volumeNodesNum += 1
            self.volumeNodesIndex.append(n)
            # get the series instance UID 
            self.referencedSeriesUID.append(seriesList[n])
            
        else:
            self.referencedSeriesUID.append('') # other modality, like SR, not used for now. 
             
        # get the Series Description 
        seriesDescription = self.db.fileValue(fileList[0], "0008,103e")
        self.seriesDescription.append(seriesDescription)
       
        
    ### find the MR filenames that match the segmentation series description names ### need to redo this. 
    print ('self.segmentationNodesIndex: ' + str(self.segmentationNodesIndex))
    print ('self.volumeNodesIndex: ' + str(self.volumeNodesIndex))
    
    # These are all the seriesDescriptions with SEG in it, or for MR/CT 
    seg_names = [self.seriesDescription[i] for i in self.segmentationNodesIndex]
    volume_names = [self.seriesDescription[i] for i in self.volumeNodesIndex]
    print ('seg_names: ' + str(seg_names))
    print ('volume_names: ' + str(volume_names))
    
    print ('referencedSeriesUID: ' + str(self.referencedSeriesUID))
    
    # For each of the segmentation scans, find the volume scan that matches
    # Based on self.referencedSeriesUID 
    print ('self.segmentationNodesIndex: ' + str(self.segmentationNodesIndex))
    seg_seriesUID = [self.referencedSeriesUID[i] for i in self.segmentationNodesIndex]
    print ('seg_series_UID: ' + str(seg_seriesUID))
    
    volume_seriesUID = [self.referencedSeriesUID[i] for i in self.volumeNodesIndex]
    volume_scan_match = [] 
    volume_names_ordered = []
    for n in range(0, self.segmentationNodesNum):
        series = seg_seriesUID[n]
        index = volume_seriesUID.index(series)
        # index into actual filelist 
        volume_scan_match.append(self.volumeNodesIndex[index])
        volume_names_ordered.append(volume_names[index])
    self.volumeNodesMatchIndex = volume_scan_match
    
    # print to check
    print ('seriesDescriptions: ' + str(self.seriesDescription))
    print ('seg_names: ' + str(seg_names))
    print ('self.segmentationNodesIndex: ' + str(self.segmentationNodesIndex))
    print ('volume_names (ordered): ' + str(volume_names_ordered))
    print ('self.volumeNodesMatchIndex: ' + str(self.volumeNodesMatchIndex))
    
    # Get the master volume loadables
    self.masterVolumeNodesLoadables = [] 
    for n in range(0, self.segmentationNodesNum):
        index = self.volumeNodesMatchIndex[n]
        fileList = self.db.filesForSeries(seriesList[index]) 
        loadables = DICOMScalarVolumePlugin.examineFiles(fileList)
        self.masterVolumeNodesLoadables.append(loadables[0])
    print ('self.masterVolumeNodesLoadables: ' + str(self.masterVolumeNodesLoadables))
    
    # Get the segmentation volume loadables
    self.segmentationNodesLoadables = [] 
    for n in range(0, self.segmentationNodesNum):
        index = self.segmentationNodesIndex[n]
        fileList = self.db.filesForSeries(seriesList[index]) 
        loadables = DICOMSegmentationPlugin.examineFiles(fileList)
        self.segmentationNodesLoadables.append(loadables[0])
    print ('self.segmentationNodesLoadables: ' + str(self.segmentationNodesLoadables))
    
    # temporary 
    for n in range(0, self.segmentationNodesNum):
        DICOMSegmentationPlugin.load(self.segmentationNodesLoadables[n])
        segmentationNodesView = list(slicer.util.getNodes('*vtkMRMLSegmentationNode*').values())[-1]
        segmentationNodesView.GetDisplayNode().SetVisibility(False)
        ID = segmentationNodesView.GetID()
        self.editorWidget.setSegmentationNode(slicer.mrmlScene.GetNodeByID(ID))

    
    ### Create the layout - one seg series per view ### 
    self.cvLogic = ViewSeriesLogic()
    viewNames = [] 
    viewNames = volume_names_ordered
    print ('viewNames: ' + str(viewNames))
    self.cvLogic.viewerPerSEG(segmentationNodes=self.segmentationNodesLoadables, \
                              masterVolumeNodes=self.masterVolumeNodesLoadables, \
                              viewNames=viewNames, \
                              layout=None, \
                              orientation='Axial',
                              opacity=0.5) 
    
   
   
  def setupEditor(self):
      
    self.editorWidget = slicer.qMRMLSegmentEditorWidget()
    self.editorWidget.setMaximumNumberOfUndoStates(10)
    self.editorWidget.setMRMLScene(slicer.mrmlScene)
    self.editorWidget.unorderedEffectsVisible = False
    self.editorWidget.setEffectNameOrder(["Paint", "Draw", "Erase", "Fill between slices", "Margin"])
    self.editorWidget.jumpToSelectedSegmentEnabled = True
    self.editorWidget.switchToSegmentationsButtonVisible = False

    # Select parameter set node if one is found in the scene, and create one otherwise
    segmentEditorSingletonTag = "mpReviewSegmentEditor"
    segmentEditorNode = slicer.mrmlScene.GetSingletonNode(segmentEditorSingletonTag, "vtkMRMLSegmentEditorNode")
    if segmentEditorNode is None:
      segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
      segmentEditorNode.SetSingletonTag(segmentEditorSingletonTag)
      segmentEditorNode = slicer.mrmlScene.AddNode(segmentEditorNode)
    if self.editorWidget.mrmlSegmentEditorNode() != segmentEditorNode:
      self.editorWidget.setMRMLSegmentEditorNode(segmentEditorNode)

    self.segmentationWidget = qt.QWidget()
    self.segmentationWidgetLayout = qt.QVBoxLayout()
    self.segmentationWidgetLayout.addWidget(self.editorWidget)
    self.segmentationWidget.setLayout(self.segmentationWidgetLayout)
    
    self.layout.addWidget(self.segmentationWidget)    



       
  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    This creates a list of the patient names from the DICOM database, which the user then must select.
    """

    # This adds the Reload & Test
    ScriptedLoadableModuleWidget.setup(self)

    # Get list of patients from slicer DICOM database 
    self.db = slicer.dicomDatabase
    patientList = list(self.db.patients())
    self.patientList = patientList
    # Get all the patient names in the database
    # For some reason, not all are listed - probably doesn't do nested names
    patientNames = []
    for patient in range(0,len(patientList)):
        studyList = self.db.studiesForPatient(patientList[patient])
        seriesList = self.db.seriesForStudy(studyList[0])
        fileList = self.db.filesForSeries(seriesList[0])
        patientNames.append(self.db.fileValue(fileList[0], "0010,0010"))
    print ('patientNames: ' + str(patientNames))

    # Display the patient names 
    # Collapsible button
    patientCollapsibleButton = ctk.ctkCollapsibleButton()
    patientCollapsibleButton.text = "Patient names"
    self.layout.addWidget(patientCollapsibleButton)

    # Try with QListWidget
    patientListWidget = qt.QListWidget()
    for patient in patientNames:
        patientListWidget.addItem(patient)

    # Layout within the patient collapsible button
    patientLayout = qt.QFormLayout(patientCollapsibleButton)
    patientLayout.addWidget(patientListWidget)

    # check if a patient name is clicked
    patientListWidget.itemClicked.connect(self.selectPatient)

    # Display the study names 
    # Collapsible button
    studyCollapsibleButton = ctk.ctkCollapsibleButton()
    studyCollapsibleButton.text = "Study names"
    self.layout.addWidget(studyCollapsibleButton)
    self.studyCollapsibleButton = studyCollapsibleButton

    self.studyListWidget = qt.QListWidget()
    self.studyLayout = qt.QFormLayout(self.studyCollapsibleButton)
    self.studyLayout.addWidget(self.studyListWidget)
    
    self.setupEditor()
    
    # ### Try wtih QListView ###
    # sampleLayout = qt.QVBoxLayout()
    # listView = qt.QListView()
    # # listView.setSpacing(3)
    # # listView.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
    # listModel = qt.QStandardItemModel()
    # item = qt.QStandardItem("Item 1")
    # listModel.appendRow(item)
    # item = qt.QStandardItem("Item 2")
    # listModel.appendRow(item)
    # item = qt.QStandardItem("Item 3")
    # listModel.appendRow(item)
    # listView.setModel(listModel)
    # # listView.show()
    # sampleLayout.addWidget(listView)

###################
# ViewSeriesLogic #
###################
# Similar to CompareVolumesLogic 

class ViewSeriesLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget
    """
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        self.sliceViewItemPattern = """
          <item><view class="vtkMRMLSliceNode" singletontag="{viewName}">
            <property name="orientation" action="default">{orientation}</property>
            <property name="viewlabel" action="default">{viewName}</property>
            <property name="viewcolor" action="default">{color}</property>
          </view></item>
         """
        # use a nice set of colors
        self.colors = slicer.util.getNode('GenericColors')
        self.lookupTable = self.colors.GetLookupTable()

    def assignLayoutDescription(self,layoutDescription):
        """assign the xml to the user-defined layout slot"""
        layoutNode = slicer.util.getNode('*LayoutNode*')
        if layoutNode.IsLayoutDescription(layoutNode.SlicerLayoutUserView):
            layoutNode.SetLayoutDescription(layoutNode.SlicerLayoutUserView, layoutDescription)
        else:
            layoutNode.AddLayoutDescription(layoutNode.SlicerLayoutUserView, layoutDescription)
        layoutNode.SetViewArrangement(layoutNode.SlicerLayoutUserView)
    
    def viewerPerSEG(self,segmentationNodes=None,masterVolumeNodes=None,viewNames=[],layout=None,orientation='Axial',opacity=0.5):
        """ Load each volume in the scene into its own
        slice viewer and link them all together.
        If background is specified, put it in the background
        of all viewers and make the other volumes be the
        forground.  If label is specified, make it active as
        the label layer of all viewers.
        Return a map of slice nodes indexed by the view name (given or generated).
        Opacity applies only when background is selected.
        """
        import math
        DICOMScalarVolumePlugin = slicer.modules.dicomPlugins['DICOMScalarVolumePlugin']()
        DICOMSegmentationPlugin = slicer.modules.dicomPlugins['DICOMSegmentationPlugin']()
        
        if masterVolumeNodes:
            print ('masterVolumeNodes were passed in -- loading')
            masterVolumeNodesView = [] 
            for n in range(0,len(masterVolumeNodes)):
                masterVolumeNode = DICOMScalarVolumePlugin.load(masterVolumeNodes[n]) 
                masterVolumeNodesView.append(masterVolumeNode)
            print ('masterVolumeNodesView: ' + str(masterVolumeNodesView))
           

        volumeCount = len(segmentationNodes)
        volumeCountSqrt = math.sqrt(volumeCount)
        if layout:
            rows = layout[0]
            columns = layout[1]
        elif volumeCountSqrt == math.floor(volumeCountSqrt):
            rows = int(volumeCountSqrt)
            columns = int(volumeCountSqrt)
        else:
            # make an array with wide screen aspect ratio
            # - e.g. 3 volumes in 3x1 grid
            # - 5 volumes 3x2 with only two volumes in second row
            c = 1.5 * volumeCountSqrt
            columns = math.floor(c)
            if (c != columns) and (volumeCount % columns != 0):
                columns += 1
            if columns > volumeCount:
                columns = volumeCount
            r = volumeCount / columns
            rows = math.floor(r)
            if r != rows:
                rows += 1

        #
        # construct the XML for the layout
        # - one viewer per volume
        # - default orientation as specified
        #
        actualViewNames = []
        index = 1
        layoutDescription = ''
        layoutDescription += '<layout type="vertical">\n'
        for row in range(int(rows)):
            layoutDescription += ' <item> <layout type="horizontal">\n'
            for column in range(int(columns)):
                try:
                    viewName = viewNames[index-1]
                except IndexError:
                    viewName = '%d_%d' % (row,column)
                rgb = [int(round(v*255)) for v in self.lookupTable.GetTableValue(index)[:-1]]
                color = '#%0.2X%0.2X%0.2X' % tuple(rgb)
                layoutDescription += self.sliceViewItemPattern.format(viewName=viewName,orientation=orientation,color=color)
                actualViewNames.append(viewName)
                index += 1
            layoutDescription += '</layout></item>\n'
        layoutDescription += '</layout>'
        self.assignLayoutDescription(layoutDescription)
        print (layoutDescription)
        
        # let the widgets all decide how big they should be
        slicer.app.processEvents()
    
        # put one of the volumes into each view, or none if it should be blank
        sliceNodesByViewName = {}
        layoutManager = slicer.app.layoutManager()
        
        print ('actualViewNames: ' + str(actualViewNames))
        
        for index in range(len(actualViewNames)):
            
            viewName = actualViewNames[index]
            print ('viewName: ' + str(viewName))
            
            try: 
                masterVolumeNodeID = masterVolumeNodesView[index].GetID()
            except: 
                masterVolumeNodeID = ""
                
            print ('masterVolumeNodeID: ' + str(masterVolumeNodeID))
            
                
            # ### This loads just the underlying masterVolumeNodeID in each view ### 
            # sliceWidget = layoutManager.sliceWidget(viewName)
            # compositeNode = sliceWidget.mrmlSliceCompositeNode() 
            # compositeNode.SetForegroundVolumeID(masterVolumeNodeID)
            # compositeNode.SetDoPropagateVolumeSelection(False) # added
            # sliceNode = sliceWidget.mrmlSliceNode()
            # sliceNode.SetOrientation(orientation)
            # sliceNodesByViewName[viewName] = sliceNode
            ### Same as above ### 
            layoutManager.sliceWidget(viewName).mrmlSliceCompositeNode().SetForegroundVolumeID(masterVolumeNodeID)
            layoutManager.sliceWidget(viewName).mrmlSliceNode().SetOrientation(orientation)
            sliceNodesByViewName[viewName] = layoutManager.sliceWidget(viewName).mrmlSliceNode()
                        
            segmentationNodesView = list(slicer.util.getNodes('*vtkMRMLSegmentationNode*').values())
            IDs = [f.GetID() for f in segmentationNodesView]
            seg_node = slicer.util.getNode(IDs[index])
            display_node = seg_node.GetDisplayNode()
            viewNameSeg = 'vtkMRMLSliceNode' + viewName
            display_node.SetDisplayableOnlyInView(viewNameSeg)
            display_node.SetVisibility(True)
            
        
        return sliceNodesByViewName

    


# #
# # ViewSeriesTest
# #
