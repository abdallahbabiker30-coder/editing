' =====================================================================
'  Trolley_Enhance_v1  -  SolidWorks VBA macro (SOLIDWORKS 2021 or newer)
'
'  Run with "Supermarket trolley.SLDPRT" OPEN and active.
'   1. Saves a backup copy:   Supermarket trolley_BACKUP.SLDPRT
'   2. Writes a report of every dimension in the model (name + value)
'      to Supermarket trolley_dimensions.txt (send this file back).
'   3. Measures the basket and asks which axis is the "depth".
'   4. Lists the dimensions that drive that size, you pick one, and the
'      macro sets it so the overall depth becomes 500 mm.
'   5. Rebuilds, checks for errors, re-measures, and saves the result as
'      Supermarket trolley_500mm.SLDPRT (your original is left unchanged).
'
'  How to run: Tools > Macro > New... > save as Trolley_Enhance.swp,
'  delete the template text, paste this whole file, press F5.
' =====================================================================
Option Explicit

Const TARGET_MM As Double = 500#     ' requested depth: 50 cm
Const TOL_MM As Double = 30#         ' how close a dimension must be to the measured size

Dim swApp As SldWorks.SldWorks
Dim swModel As SldWorks.ModelDoc2
Dim reportTxt As String
Dim candNames() As String
Dim candVals() As Double
Dim candCount As Long
Dim measuredMM As Double

Sub main()
    Set swApp = Application.SldWorks
    Set swModel = swApp.ActiveDoc
    If swModel Is Nothing Then MsgBox "Open Supermarket trolley.SLDPRT first.": Exit Sub
    If swModel.GetType <> swDocPART Then MsgBox "The active document must be a part.": Exit Sub

    Dim basePath As String
    basePath = swModel.GetPathName
    If basePath = "" Then MsgBox "Save the part once before running the macro.": Exit Sub
    basePath = Left(basePath, Len(basePath) - 7)        ' strip ".SLDPRT"

    ' ---- 1. Backup copy --------------------------------------------------
    Dim errs As Long, warns As Long
    swModel.Extension.SaveAs basePath & "_BACKUP.SLDPRT", swSaveAsCurrentVersion, _
        swSaveAsOptions_Silent + swSaveAsOptions_Copy, Nothing, errs, warns

    ' ---- 3. Measure ------------------------------------------------------
    Dim box As Variant
    box = swModel.GetPartBox(True)                       ' metres
    Dim dx As Double, dy As Double, dz As Double
    dx = (box(3) - box(0)) * 1000#
    dy = (box(4) - box(1)) * 1000#
    dz = (box(5) - box(2)) * 1000#

    Dim ax As String
    ax = UCase(Trim(InputBox( _
        "Current overall size of the trolley:" & vbCrLf & _
        "  X = " & Format(dx, "0.0") & " mm" & vbCrLf & _
        "  Y = " & Format(dy, "0.0") & " mm   (vertical in the default Front/Top setup)" & vbCrLf & _
        "  Z = " & Format(dz, "0.0") & " mm" & vbCrLf & vbCrLf & _
        "Which axis is the DEPTH you want changed to " & TARGET_MM & " mm?  (X, Y or Z)", _
        "Trolley depth", "Y")))
    Select Case ax
        Case "X": measuredMM = dx
        Case "Y": measuredMM = dy
        Case "Z": measuredMM = dz
        Case Else: MsgBox "Cancelled.": Exit Sub
    End Select

    ' ---- 2 + 4. Dimension report and candidates --------------------------
    reportTxt = "Dimension report for " & swModel.GetTitle & vbCrLf & _
        "Size X/Y/Z mm: " & Format(dx, "0.0") & " / " & Format(dy, "0.0") & " / " & Format(dz, "0.0") & vbCrLf & _
        "Depth axis chosen: " & ax & vbCrLf & String(60, "-") & vbCrLf
    candCount = 0
    Dim feat As SldWorks.Feature
    Set feat = swModel.FirstFeature
    Do While Not feat Is Nothing
        ScanFeature feat, 0
        Set feat = feat.GetNextFeature
    Loop
    WriteText basePath & "_dimensions.txt", reportTxt

    If candCount = 0 Then
        MsgBox "No single dimension is within " & TOL_MM & " mm of the measured depth (" & _
            Format(measuredMM, "0.0") & " mm)." & vbCrLf & _
            "The depth is probably built up from several plane offsets." & vbCrLf & _
            "Send me the file " & basePath & "_dimensions.txt and I will target them exactly."
        Exit Sub
    End If

    Dim lst As String, i As Long
    For i = 1 To candCount
        lst = lst & i & ")  " & candNames(i) & " = " & Format(candVals(i), "0.00") & " mm" & vbCrLf
    Next i
    Dim pick As String
    pick = InputBox("Measured depth: " & Format(measuredMM, "0.0") & " mm" & vbCrLf & _
        "Dimensions that could drive it:" & vbCrLf & lst & vbCrLf & _
        "Enter the number to change (it is adjusted so the OVERALL depth = " & TARGET_MM & " mm):", _
        "Pick depth dimension", "1")
    If Not IsNumeric(pick) Then MsgBox "Cancelled.": Exit Sub
    i = CLng(pick)
    If i < 1 Or i > candCount Then MsgBox "Invalid number.": Exit Sub

    ' keep the same offset between dimension and outside size (wire thickness etc.)
    Dim newMM As Double
    newMM = candVals(i) + (TARGET_MM - measuredMM)
    Dim swDim As SldWorks.Dimension
    Set swDim = swModel.Parameter(candNames(i))
    If swDim Is Nothing Then MsgBox "Could not access " & candNames(i): Exit Sub
    swDim.SetSystemValue3 newMM / 1000#, swSetValue_InAllConfigurations, Empty

    ' ---- 5. Rebuild + verify --------------------------------------------
    swModel.ForceRebuild3 False
    box = swModel.GetPartBox(True)
    Dim newDepth As Double
    Select Case ax
        Case "X": newDepth = (box(3) - box(0)) * 1000#
        Case "Y": newDepth = (box(4) - box(1)) * 1000#
        Case "Z": newDepth = (box(5) - box(2)) * 1000#
    End Select

    Dim errFeat As String
    errFeat = RebuildErrors()

    swModel.Extension.SaveAs basePath & "_500mm.SLDPRT", swSaveAsCurrentVersion, _
        swSaveAsOptions_Silent, Nothing, errs, warns

    MsgBox "Done." & vbCrLf & _
        candNames(i) & ": " & Format(candVals(i), "0.00") & " -> " & Format(newMM, "0.00") & " mm" & vbCrLf & _
        "Overall depth now: " & Format(newDepth, "0.0") & " mm" & vbCrLf & _
        IIf(errFeat = "", "No rebuild errors.", "Features with rebuild errors:" & vbCrLf & errFeat) & vbCrLf & vbCrLf & _
        "Saved as " & basePath & "_500mm.SLDPRT" & vbCrLf & _
        "Backup: " & basePath & "_BACKUP.SLDPRT" & vbCrLf & _
        "Report: " & basePath & "_dimensions.txt"
End Sub

Private Sub ScanFeature(feat As SldWorks.Feature, depth As Integer)
    Dim dd As SldWorks.DisplayDimension
    Dim d As SldWorks.Dimension
    Dim v As Double
    reportTxt = reportTxt & String(depth * 2, " ") & "[" & feat.GetTypeName2 & "] " & feat.Name & vbCrLf
    Set dd = feat.GetFirstDisplayDimension
    Do While Not dd Is Nothing
        Set d = dd.GetDimension2(0)
        If Not d Is Nothing Then
            v = d.SystemValue * 1000#
            reportTxt = reportTxt & String(depth * 2 + 4, " ") & d.FullName & " = " & Format(v, "0.000") & vbCrLf
            ' linear dims only (angles are radians and tiny), close to measured size
            If d.GetType <> swAngularDimension And Abs(v - measuredMM) <= TOL_MM Then AddCandidate d.FullName, v
        End If
        Set dd = feat.GetNextDisplayDimension(dd)
    Loop
    Dim subF As SldWorks.Feature
    Set subF = feat.GetFirstSubFeature
    Do While Not subF Is Nothing
        ScanFeature subF, depth + 1
        Set subF = subF.GetNextSubFeature
    Loop
End Sub

Private Sub AddCandidate(nm As String, v As Double)
    Dim k As Long
    For k = 1 To candCount
        If candNames(k) = nm Then Exit Sub
    Next k
    candCount = candCount + 1
    ReDim Preserve candNames(1 To candCount)
    ReDim Preserve candVals(1 To candCount)
    candNames(candCount) = nm
    candVals(candCount) = v
End Sub

Private Function RebuildErrors() As String
    Dim f As SldWorks.Feature, s As String, w As Boolean
    Set f = swModel.FirstFeature
    Do While Not f Is Nothing
        If f.GetErrorCode2(w) <> 0 Then s = s & "  " & f.Name & vbCrLf
        Set f = f.GetNextFeature
    Loop
    RebuildErrors = s
End Function

Private Sub WriteText(p As String, t As String)
    Dim n As Integer
    n = FreeFile
    Open p For Output As #n
    Print #n, t
    Close #n
End Sub
