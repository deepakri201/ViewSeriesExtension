# import os
# import unittest
import logging
# import vtk, qt, ctk, slicer
# from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

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

from mpReviewPreprocessor import mpReviewPreprocessorLogic

from qSlicerMultiVolumeExplorerModuleWidget import qSlicerMultiVolumeExplorerSimplifiedModuleWidget
from qSlicerMultiVolumeExplorerModuleHelper import qSlicerMultiVolumeExplorerModuleHelper as MVHelper

from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.helpers import WatchBoxAttribute
from SlicerDevelopmentToolboxUtils.widgets import TargetCreationWidget, XMLBasedInformationWatchBox
from SlicerDevelopmentToolboxUtils.icons import Icons


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
    self.parent.helpText = """
This is an example of a simple extension to view a set of series when a user clicks on a study.
The views layout contains the number of series that are in the study. The studies are populated by entries in the DICOM database."
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

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

  def selectPatient(self, item):

      """This is called when the user selects a patient name from the list.
         The corresponding study names are listed when a patient is selected.
      """

      print ('Patient ' + str(item.text()) + ' was clicked')
      self.selectPatientName = item.text()

      # Get the info from the slicer database
      # We need to find where the self.selectPatientName appears in the list of the patientNames
      db = slicer.dicomDatabase
      patientList = list(db.patients())
      patientNames = []
      for patient in range(0,len(patientList)):
          studyList = db.studiesForPatient(patientList[patient])
          seriesList = db.seriesForStudy(studyList[0])
          fileList = db.filesForSeries(seriesList[0])
          patientNames.append(db.fileValue(fileList[0], "0010,0010"))

      # Find which one it is in the list of patients
      index = patientNames.index(self.selectPatientName)
      patientNameClicked = patientNames[index]
      self.selectPatientNameIndex = index

      # Get the study names from the patient that was selected
      studyList = db.studiesForPatient(patientList[index])
      print ('studyList: ' + str(studyList)) # they are different here -- correct


      ### first remove items from study list if they exist? ####
      # https://stackoverflow.com/questions/23835847/how-to-remove-item-from-qlistwidget/23836142
      removeItems = self.studyListWidget.selectedItems()
      if not removeItems:
          return
      else:
          for item in removeItems:
              self.studyListWidget.takeItem(self.studyListWidget.row(item))

      ####### Display and populate the study names ###########

      ### Try with QListWidget - works ###
      # https://www.tutorialspoint.com/pyqt/pyqt_qlistwidget.htm
      studyListWidget = qt.QListWidget()
      # studyListWidget = self.studyListWidget
      for study in studyList:
          studyListWidget.addItem(study) # but not different here when being displayed...
      # Layout within the sample collapsible button
      # studyLayout = qt.QFormLayout(studyCollapsibleButton)
      # studyLayout = qt.QFormLayout(self.studyCollapsibleButton)
      # studyLayout.addWidget(listWidget)
      # self.layout.addWidget(listWidget) ### want to update this widget, not add a new one each time

      # see if this works?
      # studyListWidget.update()
      self.studyListWidget = studyListWidget

      # added?


      # check if a study name is clicked
      studyListWidget.itemClicked.connect(self.selectStudy)

  def selectStudy(self, item):

    """This is called when the user selects a study name from the list."""

    print ('Study ' + str(item.text()) + ' was clicked')
    self.selectStudyName = item.text()

    ### Get the index of the study that was clicked ###
    # Find which one it is in the list of studies

    db = slicer.dicomDatabase
    studyNames = db.studiesForPatient(self.selectPatientNameIndex)

    index = studyNames.index(self.selectStudyName)
    studyNameClicked = studyNames[index]
    # Get the series names from the study that was selected
    seriesList = db.seriesForStudy(studyNames[index])
    print ('seriesList: ' + str(seriesList))

    ### Get the data from each series as a node?? ###

    ### Create as many views as the number of studies ###

    ### Populate each view ###



  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    This creates a list of the patient names from the DICOM database, which the user then must select.
    """

    ### See if I can get list of patients from slicer DICOM database ###
    # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#load-dicom-files-into-the-scene-from-a-folder
    db = slicer.dicomDatabase
    patientList = list(db.patients())
    # Get all the patient names in the database
    # For some reason, not all are listed - probably doesn't do nested names
    patientNames = []
    for patient in range(0,len(patientList)):
        studyList = db.studiesForPatient(patientList[patient])
        seriesList = db.seriesForStudy(studyList[0])
        fileList = db.filesForSeries(seriesList[0])
        patientNames.append(db.fileValue(fileList[0], "0010,0010"))
    print ('patientNames: ' + str(patientNames))

    ####### Displaying the patient names ###########
    # Collapsible button
    patientCollapsibleButton = ctk.ctkCollapsibleButton()
    patientCollapsibleButton.text = "Patient names"
    self.layout.addWidget(patientCollapsibleButton)

    ### Try with QListWidget - works ###
    # https://www.tutorialspoint.com/pyqt/pyqt_qlistwidget.htm
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

    # Added?
    studyListWidget = qt.QListWidget()
    self.studyListWidget = studyListWidget

    studyLayout = qt.QFormLayout(studyCollapsibleButton)
    studyLayout.addWidget(studyListWidget)

    # patientLayout.addWidget(studyListWidget)




    # ####### Displaying the Study names ###########
    # # Collapsible button
    # sampleCollapsibleButton = ctk.ctkCollapsibleButton()
    # sampleCollapsibleButton.text = "Study names"
    # self.layout.addWidget(sampleCollapsibleButton)
    #
    # ### Try with QListWidget - works ###
    # # https://www.tutorialspoint.com/pyqt/pyqt_qlistwidget.htm
    # listWidget = qt.QListWidget()
    # listWidget.addItem("Item 1");
    # listWidget.addItem("Item 2");
    # listWidget.addItem("Item 3");
    # # Layout within the sample collapsible button
    # sampleLayout = qt.QFormLayout(sampleCollapsibleButton)
    # sampleLayout.addWidget(listWidget)



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




#
# ViewSeriesLogic
#

class ViewSeriesLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")

  def process(self, inputVolume, outputVolume, imageThreshold, invert=False, showResult=True):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    :param inputVolume: volume to be thresholded
    :param outputVolume: thresholding result
    :param imageThreshold: values above/below this threshold will be set to 0
    :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
    :param showResult: show output volume in slice viewers
    """

    if not inputVolume or not outputVolume:
      raise ValueError("Input or output volume is invalid")

    import time
    startTime = time.time()
    logging.info('Processing started')

    # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
    cliParams = {
      'InputVolume': inputVolume.GetID(),
      'OutputVolume': outputVolume.GetID(),
      'ThresholdValue' : imageThreshold,
      'ThresholdType' : 'Above' if invert else 'Below'
      }
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
    # We don't need the CLI module node anymore, remove it to not clutter the scene with it
    slicer.mrmlScene.RemoveNode(cliNode)

    stopTime = time.time()
    logging.info('Processing completed in {0:.2f} seconds'.format(stopTime-startTime))

#
# ViewSeriesTest
#
