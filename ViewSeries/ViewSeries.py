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
# December 2021
# Brigham and Women's Hospital
################################################################################

from slicer.util import VTKObservationMixin
import numpy as np 

# from __future__ import division
import os, json, xml.dom.minidom, string, glob, re, math
import vtk, qt, ctk, slicer
import logging
import CompareVolumes
from Editor import EditorWidget
from EditorLib.EditUtil import EditUtil
import SimpleITK as sitk
import sitkUtils
import datetime
from slicer.ScriptedLoadableModule import *

# from mpReviewPreprocessor import mpReviewPreprocessorLogic
#
# from qSlicerMultiVolumeExplorerModuleWidget import qSlicerMultiVolumeExplorerSimplifiedModuleWidget
# from qSlicerMultiVolumeExplorerModuleHelper import qSlicerMultiVolumeExplorerModuleHelper as MVHelper
#
# from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin
# from SlicerDevelopmentToolboxUtils.helpers import WatchBoxAttribute
# from SlicerDevelopmentToolboxUtils.widgets import TargetCreationWidget, XMLBasedInformationWatchBox
# from SlicerDevelopmentToolboxUtils.icons import Icons

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

      ### There must be a better way to do this! Fix later ###
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

    ### Get the index of the study that was clicked ###
    # Find which one it is in the list of studies

    # patientList = list(self.db.patients())
    index = self.patientNames.index(self.selectPatientName)
    # print ("index of the patient: " + str(index))

    # print ('selectPatientNameIndex: ' + str(self.selectPatientNameIndex))
    # studyNames = db.studiesForPatient(self.selectPatientNameIndex)
    # studyNames = db.studiesForPatient(index)
    # studyNames = self.db.studiesForPatient(patientList[index])
    studyNames = self.db.studiesForPatient(self.patientList[index])
    # print ('studyNames: ' + str(studyNames))

    index = studyNames.index(self.selectStudyName)
    studyNameClicked = studyNames[index]
    # Get the series names from the study that was selected
    seriesList = self.db.seriesForStudy(studyNames[index])
    print ('seriesList: ' + str(seriesList))
    self.seriesListNum = len(seriesList)
    print ('number of series: ' + str(self.seriesListNum))

    ### Get the data from each series as a node and store in self.volumeNodes
    # Should not use slicer.util.loadVolume to load a DICOM file, as we may have a 
    # series of DICOM files. Better to use the plugin below. 
    
    # for the scalar volumes 
    DICOMScalarVolumePlugin = slicer.modules.dicomPlugins['DICOMScalarVolumePlugin']()
    # for the SEG label volumes 
    DICOMSegmentationPlugin = slicer.modules.dicomPlugins['DICOMSegmentationPlugin']()
    # for RTSTRUCT 
    DicomRtImportExportPlugin = slicer.modules.dicomPlugins['DicomRtImportExportPlugin']()
    
    ################# Instead, we want to get the number of SEG files #########
    
    ### Get the series that have SEG files ###

    self.segmentationNodesNum = 0
    self.segmentationNodesIndex = [] 
    self.volumeNodesNum = 0 
    self.volumeNodesIndex = [] 
    self.seriesDescription = [] 
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
            # DICOMSegmentationPlugin.load(loadables[0]) # this returns True! As it does according to documentation.
            self.segmentationNodesNum += 1 
            self.segmentationNodesIndex.append(n)
        if (modality=="MR"):
            loadables = DICOMScalarVolumePlugin.examineFiles(fileList)
            self.volumeNodesNum += 1
            self.volumeNodesIndex.append(n)
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
    
    # For each of the segmentation scans, find the volume scan that matches
    volume_scan_match = []
    volume_names_ordered = []  
    for n in range(0, self.segmentationNodesNum):
        print ('n: ' + str(n))
        seg_name = seg_names[n]
        print ('seg_name to find match for: ' + str(seg_name))
        for m in range(0, self.volumeNodesNum):
            volume_name = volume_names[m]
            if (volume_name in seg_name):
                volume_scan_match.append(self.volumeNodesIndex[m]) # this is the index into the actual filelist. 
                volume_names_ordered.append(volume_names[m])
                # print the matching volume name just to check 
                print ('found matching volume name: ' + str(volume_names[m]))
    self.volumeNodesMatchIndex = volume_scan_match 
    
    # print to check
    print ('seriesDescriptions: ' + str(self.seriesDescription))
    print ('seg_names: ' + str(seg_names))
    print ('self.segmentationNodesIndex: ' + str(self.segmentationNodesIndex))
    print ('volume_names (ordered): ' + str(volume_names_ordered))
    print ('self.volumeNodesMatchIndex: ' + str(self.volumeNodesMatchIndex))
    
    
    self.masterVolumeNodesLoadables = [] 
    for n in range(0, self.segmentationNodesNum):
        index = self.volumeNodesMatchIndex[n]
        fileList = self.db.filesForSeries(seriesList[index]) 
        loadables = DICOMScalarVolumePlugin.examineFiles(fileList)
        self.masterVolumeNodesLoadables.append(loadables[0])
    print ('self.masterVolumeNodesLoadables: ' + str(self.masterVolumeNodesLoadables))
    
    
    self.segmentationNodesLoadables = [] 
    for n in range(0, self.segmentationNodesNum):
        index = self.segmentationNodesIndex[n]
        fileList = self.db.filesForSeries(seriesList[index]) 
        loadables = DICOMSegmentationPlugin.examineFiles(fileList)
        self.segmentationNodesLoadables.append(loadables[0])
    print ('self.segmentationNodesLoadables: ' + str(self.segmentationNodesLoadables))
    
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
    
    
    # # Create a list of the 'master nodes' that matches each seg.  
    # self.masterVolumeNodes = [] 
    # for n in range(0, self.segmentationNodesNum):
    #     index = self.volumeNodesMatchIndex[n]
    #     fileList = self.db.filesForSeries(seriesList[index]) 
    #     loadables = DICOMScalarVolumePlugin.examineFiles(fileList)
    #     masterVolumeNode = DICOMScalarVolumePlugin.load(loadables[0]) 
    #     self.masterVolumeNodes.append(masterVolumeNode)
    # print ('self.masterVolumeNodes: ' + str(self.masterVolumeNodes))
     
    # # Load the segmentation nodes that are in the scene 
    # self.segmentationNodes = [] 
    # for n in range(0,self.segmentationNodesNum): 
    #     id = 'vtkMRMLSegmentationNode' + str(n+1)
    #     print ('id: ' + str(id))
    #     segmentationNode = slicer.mrmlScene.GetNodeByID(id)
    #     self.segmentationNodes.append(segmentationNode) 
    # print ('segmentationNodes: ' + str(self.segmentationNodes))
    #
    # ### Save out each of the segmentation nodes ### 
    # temp_dir = r"C:\Users\deepa\deepa\3DSlicer\temp" # will change later
    # for n in range(0,self.segmentationNodesNum):
    #     if not os.path.isdir(temp_dir):
    #         os.mkdir(temp_dir)
    #     # save refernce volume
    #     masterVolumeNode = self.masterVolumeNodes[n] 
    #     filepath = os.path.join(temp_dir, 'masterVolumeNode_' + str(n) + '.nrrd')
    #     print ('masterVolumeNode filepath: ' + str(filepath))
    #     slicer.util.saveNode(masterVolumeNode, filepath)
    #     # save seg volume
    #     segmentationNode = self.segmentationNodes[n]
    #     filepath = os.path.join(temp_dir, 'segmentationNode_' + str(n) + '.seg.nrrd')
    #     print ('segmentationNode filepath: ' + str(filepath))
    #     # segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(referenceVolumeNode)
    #     slicer.util.saveNode(segmentationNode, filepath)
    #
    #
    #
    # ### Remove everything from the scene ###
    # print ('Removing all nodes from scene as a test') 
    # for n in range(0,self.segmentationNodesNum):
    #     slicer.mrmlScene.RemoveNode(self.segmentationNodes[n])
    #     slicer.mrmlScene.RemoveNode(self.masterVolumeNodes[n])
    #
    # print ('nodes after deleting')    
    # print ('segmentationNodes: ' + str(self.segmentationNodes))
    # print ('masterVolumeNodes: ' + str(self.masterVolumeNodes))
    #
    # ### Then load them in again, but not show? ### 
    # for n in range(0,self.segmentationNodesNum):
    #     filename = os.path.join(temp_dir, 'segmentationNode_' + str(n) + '.seg.nrrd')
    #     self.segmentationNodes[n] = slicer.util.loadSegmentation(filename)
    #     filename = os.path.join(temp_dir, 'masterVolumeNode_' + str(n) + '.nrrd')
    #     self.masterVolumeNodes[n] = slicer.util.loadVolume(filename)
    #
    # print ('nodes after reloading')  
    # print ('segmentationNodes: ' + str(self.segmentationNodes))
    # print ('masterVolumeNodes: ' + str(self.masterVolumeNodes))
    #
    #
    #
    #
    # ### Create the layout - one seg series per view ### 
    # self.cvLogic = ViewSeriesLogic()
    # viewNames = [] 
    # viewNames = volume_names_ordered
    # print ('viewNames: ' + str(viewNames))
    # # for n in range(0,self.segmentationNodesNum):
    #     # index = self.volumeNodesIndex[n]
    #     # print ('index: ' + str(index))
    #     # viewName = self.seriesDescription[index]
    #     # print ('viewName: ' + str(viewName))
    #     # viewNames.append(viewName)
    # self.cvLogic.viewerPerSEG(segmentationNodes=self.segmentationNodes, \
    #                           masterVolumeNodes=self.masterVolumeNodes, \
    #                           viewNames=viewNames, \
    #                           layout=None, \
    #                           orientation='Axial',
    #                           opacity=0.5) 
    


    
    ################################### Extra code, delete later ##########################
    
    #
    # print ('segmentationNodes: ' + str(self.segmentationNodes))
    # print ('masterNodeVolume: ' + str(self.masterNodeVolume))
    
    ### Load in temp files ###    
    
    # # Convert seg to label maps using appropriate master node as reference 
    # # https://gist.github.com/lassoan/5ad51c89521d3cd9c5faf65767506b37 
    #
    # self.labelmapVolumeNodes = [] 
    # for n in range(0,self.segmentationNodesNum):
    #     segmentationNode = self.segmentationNodes[n] 
    #     segmentNames = ["Normal", "Peripheral zone of the prostate", "Lesion", "Prostate"] # get automatically later.
    #     segmentIds = vtk.vtkStringArray()
    #     for segmentName in segmentNames:
    #         segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)
    #         segmentIds.InsertNextValue(segmentId)
    #     labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    #     # Get the master node from the MR/CT file that matches: 
    #     masterVolumeNode = self.masterNodeVolume[n] # FOR NOW, CHANGE LATER. 
    #     # slicer.vtkSlicerSegmentationsModuleLogic.ExportAllSegmentsToLabelmapNode(segmentationNode,labelmapVolumeNode) # include master node
    #     # slicer.vtkSlicerSegmentationsModuleLogic.ExportAllSegmentsToLabelmapNode(segmentationNode,labelmapVolumeNode, masterVolumeNode) # include master node
    #     # slicer.vtkSlicerSegmentationsModuleLogic.ExportVisibleSegmentsToLabelmapNode(segmentationNode,labelmapVolumeNode, masterVolumeNode) # include master node
    #
    #     self.labelmapVolumeNodes.append(labelmapVolumeNode)
    #
    #     # save the node 
    #     temp_dir = r"C:\Users\deepa\deepa\3DSlicer\temp" # will change later
    #     temp_filename = os.path.join(temp_dir, str(n)+'.seg.nrrd')
    #     if not os.path.isdir(temp_dir):
    #         os.mkdir(temp_dir)
    #     slicer.util.saveNode(labelmapVolumeNode, temp_filename)
    #
    # print ('self.labelmapVolumeNodes: ' + str(self.labelmapVolumeNodes)
    
    
    
    # Remove the seg nodes 
    
    # Load the label map nodes 
    
    # Use viewerPerSEG, with a different background volume for each? 

    # # https://discourse.slicer.org/t/export-segmentation-to-labelmap-using-python/6801
    # # https://gist.github.com/lassoan/5ad51c89521d3cd9c5faf65767506b37 to export all segments  
    # # Then can define a master node  
    #
    # # Then use 
    #
    #
    # ########## Method 1 - try converting seg to label maps and pass that into viewerperSEG ######
    #
    # # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html
    # # Section "Export labelmap node from segmentation node" 
    # # In this way, the labelmapVolumeNode is populated 
    # # self.labelmapVolumeNodes = [] 
    # # for n in range(0,self.segmentationNodesNum):
    # #     segmentationNode = self.segmentationNodes[n] 
    # #     segmentNames = ["Normal", "Peripheral zone of the prostate", "Lesion", "Prostate"] # get automatically later.
    # #     segmentIds = vtk.vtkStringArray()
    # #     for segmentName in segmentNames:
    # #       segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)
    # #       segmentIds.InsertNextValue(segmentId)
    # #     labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    # #     slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(segmentationNode, segmentIds, labelmapVolumeNode)
    # #     # slicer.vtkSlicerSegmentationsModuleLogic.ExportAllSegmentsToLabelmapNode(segmentationNode, labelmapVolumeNode)
    #
    # self.labelmapVolumeNodes = [] 
    # for n in range(0,self.segmentationNodesNum):
    #     segmentationNode = self.segmentationNodes[n] 
    #     segmentNames = ["Normal", "Peripheral zone of the prostate", "Lesion", "Prostate"] # get automatically later.
    #     segmentIds = vtk.vtkStringArray()
    #     for segmentName in segmentNames:
    #         segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)
    #         segmentIds.InsertNextValue(segmentId)
    #     labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    #     # Get the master node from the MR/CT file that matches: 
    #     masterVolumeNode = self.masterNodeVolume[n] # FOR NOW, CHANGE LATER. 
    #     # slicer.vtkSlicerSegmentationsModuleLogic.ExportAllSegmentsToLabelmapNode(segmentationNode,labelmapVolumeNode) # include master node
    #     # slicer.vtkSlicerSegmentationsModuleLogic.ExportAllSegmentsToLabelmapNode(segmentationNode,labelmapVolumeNode, masterVolumeNode) # include master node
    #     slicer.vtkSlicerSegmentationsModuleLogic.ExportVisibleSegmentsToLabelmapNode(segmentationNode,labelmapVolumeNode, masterVolumeNode) # include master node
    #
    #
    #
    #     self.labelmapVolumeNodes.append(labelmapVolumeNode)
    #     # save the node 
    #     temp_dir = r"C:\Users\deepa\deepa\3DSlicer\temp" # will change later
    #     temp_filename = os.path.join(temp_dir, str(n)+'.seg.nrrd')
    #     if not os.path.isdir(temp_dir):
    #         os.mkdir(temp_dir)
    #     slicer.util.saveNode(labelmapVolumeNode, temp_filename)
    #
    # print ('self.labelmapVolumeNodes: ' + str(self.labelmapVolumeNodes))
    #
    # print ('Now delete the segmentation nodes')
    # for n in range(0,self.segmentationNodesNum):
    #     slicer.mrmlScene.RemoveNode(self.segmentationNodes[n])
    #
    # self.cvLogic = ViewSeriesLogic()
    # self.cvLogic.viewerPerSEG(labelNodes=self.labelmapVolumeNodes, \
    #                       viewNames=['A', 'B', 'C'], \
    #                       layout=None, \
    #                       orientation='Axial',
    #                       opacity=0.5) 


    ######## Method 2 - save out segmentations as .seg.nrrd files #####
    
    # Save out seg as .seg.nrrd files 
    
    # remove seg nodes from scene - because it adds all to the viewers 
    
    # load in .seg.nrrd files and display using viewerperSEG 
    
    # ### Save out the segmentationNodes temporarily as nrrd files ### 
    # tempDir = os.path.join()
    # labelFileName = os.path.join(segmentationsDir, uniqueID + '.nrrd')
    # sNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
    # sNode.SetFileName(labelFileName)
    # sNode.SetWriteFileFormat('nrrd')
    # sNode.SetURI(None)
    # success = sNode.WriteData(label)
    
    ### Load nrrd files into label nodes ### 

    
    ### Get the matching MR/CT ones to the SEG files 
    
    ### load both as composite nodes 
    
    



  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    This creates a list of the patient names from the DICOM database, which the user then must select.
    """

    # This adds the Reload & Test
    ScriptedLoadableModuleWidget.setup(self)

    ### See if I can get list of patients from slicer DICOM database ###
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

    ####### Displaying the patient names ###########
    # Collapsible button
    patientCollapsibleButton = ctk.ctkCollapsibleButton()
    patientCollapsibleButton.text = "Patient names"
    self.layout.addWidget(patientCollapsibleButton)

    ### Try with QListWidget - works ###
    patientListWidget = qt.QListWidget()
    for patient in patientNames:
        patientListWidget.addItem(patient)

    # Layout within the patientcollapsible button
    patientLayout = qt.QFormLayout(patientCollapsibleButton)
    patientLayout.addWidget(patientListWidget)

    # check if a patient name is clicked
    patientListWidget.itemClicked.connect(self.selectPatient)

    ###### Creating a layout for the study names #####

    # Collapsible button
    studyCollapsibleButton = ctk.ctkCollapsibleButton()
    studyCollapsibleButton.text = "Study names"
    self.layout.addWidget(studyCollapsibleButton)
    self.studyCollapsibleButton = studyCollapsibleButton

    self.studyListWidget = qt.QListWidget()
    self.studyLayout = qt.QFormLayout(self.studyCollapsibleButton)
    self.studyLayout.addWidget(self.studyListWidget)

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

        # if the nodes don't exist, load from scene 
        if not segmentationNodes:
            print ('segmentationNodes were not passed in -- loading from scene')
            segmentationNodesView = list(slicer.util.getNodes('*vtkMRMLSegmentationNode*').values())
        # if they do exist, they still need to be loaded 
        else:
            print ('segmentationNodes were passed in -- loading')
            segmentationNodesView = [] 
            for n in range(0,len(segmentationNodes)):
                segmentationNode = DICOMSegmentationPlugin.load(segmentationNodes[n]) # the node is not returned, only True. 
                segmentationNodesView.append(segmentationNode)
        print ('segmentationNodesView: ' + str(segmentationNodesView))
        
        # if the nodes don't exist, load from scene 
        if not masterVolumeNodes: 
            print ('masterVolumeNodes were not passed in -- loading from scene')
            masterVolumeNodesView = list(slicer.util.getNodes('*VolumeNode*').values())
        # if they do exist, they still need to be loaded 
        else: 
            print ('masterVolumeNodes were passed in -- loading')
            masterVolumeNodesView = [] 
            for n in range(0,len(masterVolumeNodes)):
                masterVolumeNode = DICOMScalarVolumePlugin.load(masterVolumeNodes[n]) 
                masterVolumeNodesView.append(masterVolumeNode)
        print ('masterVolumeNodesView: ' + str(masterVolumeNodesView))
        
        # volumeNodes = list(slicer.util.getNodes('*LabelMapVolumeNode*').values()) 
        # labelNodes = list(slicer.util.getNodes('*-label*').values()) # from line 755 in mpReview 
        # volumeNodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
            
        if len(segmentationNodesView) == 0:
            return

        volumeCount = len(segmentationNodesView)
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
            
            try:
                segmentationNodeID = segmentationNodesView[index].GetID()
            except IndexError:
                segmentationNodeID = ""
                
            # print ('masterVolumeNodeID: ' + str(masterVolumeNodeID))
            # print ('segmentationNodeID: ' + str(segmentationNodeID))
                
            
            sliceWidget = layoutManager.sliceWidget(viewName)
            
            compositeNode = sliceWidget.mrmlSliceCompositeNode()
            compositeNode.SetBackgroundVolumeID(masterVolumeNodeID)
            compositeNode.SetLabelVolumeID(segmentationNodeID) # why is this set in each view?? 
            
            sliceNode = sliceWidget.mrmlSliceNode()
            sliceNode.SetOrientation(orientation)
            sliceNodesByViewName[viewName] = sliceNode
        
        return sliceNodesByViewName
    
  # def viewerPerSEG(self,labelNodes=None,viewNames=[],layout=None,orientation='Axial',opacity=0.5):
  #   """ Load each volume in the scene into its own
  #   slice viewer and link them all together.
  #   If background is specified, put it in the background
  #   of all viewers and make the other volumes be the
  #   forground.  If label is specified, make it active as
  #   the label layer of all viewers.
  #   Return a map of slice nodes indexed by the view name (given or generated).
  #   Opacity applies only when background is selected.
  #   """
  #   import math
  #
  #   if not labelNodes:
  #     # volumeNodes = list(slicer.util.getNodes('*VolumeNode*').values())
  #     # volumeNodes = list(slicer.util.getNodes('*LabelMapVolumeNode*').values()) 
  #     labelNodes = list(slicer.util.getNodes('*-label*').values()) # from line 755 in mpReview 
  #     # volumeNodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
  #
  #     print ('labelNodes: ' + str(labelNodes))
  #
  #   if len(labelNodes) == 0:
  #     return
  #
  #   volumeCount = len(labelNodes)
  #   volumeCountSqrt = math.sqrt(volumeCount)
  #   if layout:
  #     rows = layout[0]
  #     columns = layout[1]
  #   elif volumeCountSqrt == math.floor(volumeCountSqrt):
  #     rows = int(volumeCountSqrt)
  #     columns = int(volumeCountSqrt)
  #   else:
  #     # make an array with wide screen aspect ratio
  #     # - e.g. 3 volumes in 3x1 grid
  #     # - 5 volumes 3x2 with only two volumes in second row
  #     c = 1.5 * volumeCountSqrt
  #     columns = math.floor(c)
  #     if (c != columns) and (volumeCount % columns != 0):
  #       columns += 1
  #     if columns > volumeCount:
  #       columns = volumeCount
  #     r = volumeCount / columns
  #     rows = math.floor(r)
  #     if r != rows:
  #       rows += 1
  #
  #   #
  #   # construct the XML for the layout
  #   # - one viewer per volume
  #   # - default orientation as specified
  #   #
  #   actualViewNames = []
  #   index = 1
  #   layoutDescription = ''
  #   layoutDescription += '<layout type="vertical">\n'
  #   for row in range(int(rows)):
  #     layoutDescription += ' <item> <layout type="horizontal">\n'
  #     for column in range(int(columns)):
  #       try:
  #         viewName = viewNames[index-1]
  #       except IndexError:
  #         viewName = '%d_%d' % (row,column)
  #       rgb = [int(round(v*255)) for v in self.lookupTable.GetTableValue(index)[:-1]]
  #       color = '#%0.2X%0.2X%0.2X' % tuple(rgb)
  #       layoutDescription += self.sliceViewItemPattern.format(viewName=viewName,orientation=orientation,color=color)
  #       actualViewNames.append(viewName)
  #       index += 1
  #     layoutDescription += '</layout></item>\n'
  #   layoutDescription += '</layout>'
  #   self.assignLayoutDescription(layoutDescription)
  #
  #   # let the widgets all decide how big they should be
  #   slicer.app.processEvents()
  #
  #   # put one of the volumes into each view, or none if it should be blank
  #   sliceNodesByViewName = {}
  #   layoutManager = slicer.app.layoutManager()
  #
  #   print ('actualViewNames: ' + str(actualViewNames))
  #
  #   for index in range(len(actualViewNames)):
  #       viewName = actualViewNames[index]
  #       print ('viewName: ' + str(viewName))
  #       try:
  #           labelNodeID = labelNodes[index].GetID()
  #       except IndexError:
  #           labelNodeID = ""
  #       # print ('labelNodeID: ' + str(labelNodeID))
  #       sliceWidget = layoutManager.sliceWidget(viewName)
  #       compositeNode = sliceWidget.mrmlSliceCompositeNode()
  #       # if (label):
  #       #     compositeNode.SetLabelVolumeID(labelNodes[index].GetID())
  #       # else:
  #       #     compositeNode.SetLabelVolumeID("")
  #       # compositeNode.SetLabelVolumeID(labelNodes[index].GetID())
  #       compositeNode.SetLabelVolumeID(labelNodeID)
  #
  #
  #       sliceNode = sliceWidget.mrmlSliceNode()
  #       sliceNode.SetOrientation(orientation)
  #       sliceNodesByViewName[viewName] = sliceNode
  #
  #   return sliceNodesByViewName

    


# #
# # ViewSeriesTest
# #
