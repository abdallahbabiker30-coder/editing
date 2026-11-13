' =====================================================================
'  Trolley_Enhance_v2  -  SolidWorks VBA macro (SOLIDWORKS 2021 or newer)
'  Written for "Supermarket trolley.SLDPRT" using its dimension report.
'
'  Run with the ORIGINAL trolley part open and active. It does:
'   0. Backup copy  ->  <name>_BACKUP_v2.SLDPRT
'   1. DEPTH: sets one size of the main basket sketch "BB" to 500 mm
'      (D1@BB = 450 height, D2@BB = 350 width, D3@BB = 750 length)
'      and can move Plane27 (the top slope cut) by the same amount.
'   2. JOINTS: slightly larger blends at the wire joints
'      Fillet1/Fillet2 1.0 -> 1.5 mm,  Fillet3/Fillet4 3.0 -> 4.0 mm
'   3. FINISHING: rounds every free wire end (no sharp cut ends),
'      one fillet feature per wire size, named "Rounded ends D..".
'  Every step is tried on its own; if it causes a rebuild error it is
'  undone automatically and listed as SKIPPED in the log.
'   4. Saves <name>_enhanced.SLDPRT and <name>_enhance_log.txt
'
'  How to run: Tools > Macro > New... > save as Trolley_Enhance_v2.swp,
'  delete the template text, paste this whole file, press F5.
' =====================================================================
Option Explicit

Const TARGET_MM As Double = 500#

Dim swApp As SldWorks.SldWorks
Dim swModel As SldWorks.ModelDoc2
Dim logTxt As String

Sub main()
    Set swApp = Application.SldWorks
    Set swModel = swApp.ActiveDoc
    If swModel Is Nothing Then MsgBox "Open Supermarket trolley.SLDPRT first.": Exit Sub
    If swModel.GetType <> swDocPART Then MsgBox "The active document must be a part.": Exit Sub
    Dim basePath As String
    basePath = swModel.GetPathName
    If basePath = "" Then MsgBox "Save the part once before running the macro.": Exit Sub
    basePath = Left(basePath, Len(basePath) - 7)

    Dim errs As Long, warns As Long
    swModel.Extension.SaveAs basePath & "_BACKUP_v2.SLDPRT", swSaveAsCurrentVersion, _
        swSaveAsOptions_Silent + swSaveAsOptions_Copy, Nothing, errs, warns

    swModel.ForceRebuild3 False
    Dim startErr As String
    startErr = RebuildErrors()
    logTxt = "Trolley enhance v2 log - " & swModel.GetTitle & vbCrLf & _
        "Size before (X/Y/Z mm): " & SizeText() & vbCrLf
    If startErr <> "" Then logTxt = logTxt & "Rebuild errors already present before changes:" & vbCrLf & startErr

    ' ---- 1. Depth ----------------------------------------------------------
    Dim h As Double, w As Double, l As Double
    h = DimMM("D1@BB"): w = DimMM("D2@BB"): l = DimMM("D3@BB")
    If h < 0 Then MsgBox "Sketch BB was not found - is this the trolley part?": Exit Sub

    Dim pick As String
    pick = InputBox("Main basket sketch BB:" & vbCrLf & _
        "  1)  D1@BB = " & Format(h, "0.0") & " mm   (height / how deep the basket is)" & vbCrLf & _
        "  2)  D2@BB = " & Format(w, "0.0") & " mm   (width)" & vbCrLf & _
        "  3)  D3@BB = " & Format(l, "0.0") & " mm   (length, front to back)" & vbCrLf & vbCrLf & _
        "Which one is the DEPTH to set to " & TARGET_MM & " mm?" & vbCrLf & _
        "(0 = skip the depth change)", "Trolley depth", "1")
    If pick = "" Then MsgBox "Cancelled.": Exit Sub

    If pick <> "0" Then
        Dim dName As String, oldV As Double
        Select Case pick
            Case "1": dName = "D1@BB": oldV = h
            Case "2": dName = "D2@BB": oldV = w
            Case "3": dName = "D3@BB": oldV = l
            Case Else: MsgBox "Invalid choice.": Exit Sub
        End Select
        Dim delta As Double
        delta = TARGET_MM - oldV
        If TrySetDim(dName, TARGET_MM, "Depth " & dName) Then
            Dim p27 As Double
            p27 = DimMM("D1@Plane27")
            If p27 > 0 And Abs(delta) > 0.001 Then
                If MsgBox("Depth changed by " & Format(delta, "+0.0;-0.0") & " mm." & vbCrLf & _
                    "Look at the model now: if the top sloped cut (Cut-Extrude1 on Plane27, " & _
                    Format(p27, "0.0") & " mm) now cuts the basket in the wrong place," & vbCrLf & _
                    "click YES to move Plane27 by the same " & Format(delta, "+0.0;-0.0") & " mm." & vbCrLf & _
                    "Click NO to leave it.", vbYesNo + vbQuestion, "Top cut plane") = vbYes Then
                    TrySetDim "D1@Plane27", p27 + delta, "Plane27 follows depth"
                End If
            End If
        End If
    End If

    ' ---- 2. Joint blends ----------------------------------------------------
    TryScaleDim "D1@Fillet1", 1.5, "Joint blend Fillet1"
    TryScaleDim "D1@Fillet2", 1.5, "Joint blend Fillet2"
    TryScaleDim "D1@Fillet3", 4#, "Joint blend Fillet3"
    TryScaleDim "D1@Fillet4", 4#, "Joint blend Fillet4"

    ' ---- 3. Round the free wire ends ---------------------------------------
    RoundWireEnds

    ' ---- 4. Save -----------------------------------------------------------
    swModel.ForceRebuild3 False
    logTxt = logTxt & "Size after (X/Y/Z mm): " & SizeText() & vbCrLf
    Dim endErr As String
    endErr = RebuildErrors()
    logTxt = logTxt & IIf(endErr = "", "No rebuild errors at the end." & vbCrLf, _
        "Rebuild errors at the end:" & vbCrLf & endErr)

    swModel.Extension.SaveAs basePath & "_enhanced.SLDPRT", swSaveAsCurrentVersion, _
        swSaveAsOptions_Silent, Nothing, errs, warns
    WriteText basePath & "_enhance_log.txt", logTxt
    MsgBox logTxt & vbCrLf & "Saved: " & basePath & "_enhanced.SLDPRT", vbInformation, "Trolley enhance v2"
End Sub

' ---------- helpers --------------------------------------------------------
Private Function DimMM(nm As String) As Double
    Dim d As SldWorks.Dimension
    Set d = swModel.Parameter(nm)
    If d Is Nothing Then DimMM = -1 Else DimMM = d.SystemValue * 1000#
End Function

Private Function TrySetDim(nm As String, newMM As Double, label As String) As Boolean
    Dim d As SldWorks.Dimension
    Set d = swModel.Parameter(nm)
    If d Is Nothing Then logTxt = logTxt & "SKIPPED  " & label & " (" & nm & " not found)" & vbCrLf: Exit Function
    Dim oldMM As Double
    oldMM = d.SystemValue * 1000#
    d.SetSystemValue3 newMM / 1000#, swSetValue_InAllConfigurations, Empty
    swModel.ForceRebuild3 False
    Dim e As String
    e = RebuildErrors()
    If e <> "" Then
        d.SetSystemValue3 oldMM / 1000#, swSetValue_InAllConfigurations, Empty
        swModel.ForceRebuild3 False
        logTxt = logTxt & "SKIPPED  " & label & ": " & Format(newMM, "0.0") & " mm caused errors in" & vbCrLf & e & _
            "         (restored to " & Format(oldMM, "0.0") & " mm)" & vbCrLf
    Else
        logTxt = logTxt & "DONE     " & label & ": " & nm & " " & Format(oldMM, "0.0") & " -> " & Format(newMM, "0.0") & " mm" & vbCrLf
        TrySetDim = True
    End If
End Function

' only enlarges, never shrinks a value the user already set bigger
Private Sub TryScaleDim(nm As String, newMM As Double, label As String)
    Dim cur As Double
    cur = DimMM(nm)
    If cur < 0 Then logTxt = logTxt & "SKIPPED  " & label & " (not found)" & vbCrLf: Exit Sub
    If cur >= newMM Then logTxt = logTxt & "KEPT     " & label & " already " & Format(cur, "0.0") & " mm" & vbCrLf: Exit Sub
    TrySetDim nm, newMM, label
End Sub

' Free wire ends = planar faces bounded by one circular edge (radius <= 3.1 mm).
' Each wire size gets its own fillet of 40 % of the wire radius.
Private Sub RoundWireEnds()
    Dim part As SldWorks.PartDoc
    Set part = swModel
    Dim bodies As Variant
    bodies = part.GetBodies2(swSolidBody, True)
    If IsEmpty(bodies) Then Exit Sub

    Dim radii(1 To 10) As Double, nR As Long
    Dim edgeSets(1 To 10) As Collection
    Dim i As Long, j As Long, k As Long

    For i = 0 To UBound(bodies)
        Dim b As SldWorks.Body2
        Set b = bodies(i)
        Dim faces As Variant
        faces = b.GetFaces
        If Not IsEmpty(faces) Then
            For j = 0 To UBound(faces)
                Dim f As SldWorks.Face2
                Set f = faces(j)
                Dim s As SldWorks.Surface
                Set s = f.GetSurface
                If s.IsPlane Then
                    Dim eds As Variant
                    eds = f.GetEdges
                    If Not IsEmpty(eds) Then
                        If UBound(eds) = 0 Then
                            Dim ed As SldWorks.Edge
                            Set ed = eds(0)
                            Dim c As SldWorks.Curve
                            Set c = ed.GetCurve
                            If c.IsCircle Then
                                Dim cp As Variant, r As Double
                                cp = c.CircleParams
                                r = Round(cp(6) * 1000#, 2)
                                If r > 0.4 And r <= 3.1 Then
                                    Dim slot As Long
                                    slot = 0
                                    For k = 1 To nR
                                        If Abs(radii(k) - r) < 0.05 Then slot = k
                                    Next k
                                    If slot = 0 And nR < 10 Then
                                        nR = nR + 1: radii(nR) = r
                                        Set edgeSets(nR) = New Collection
                                        slot = nR
                                    End If
                                    If slot > 0 Then edgeSets(slot).Add ed
                                End If
                            End If
                        End If
                    End If
                End If
            Next j
        End If
    Next i

    If nR = 0 Then logTxt = logTxt & "INFO     no free circular wire ends found" & vbCrLf: Exit Sub

    Dim selMgr As SldWorks.SelectionMgr
    Set selMgr = swModel.SelectionManager
    For k = 1 To nR
        swModel.ClearSelection2 True
        Dim sd As SldWorks.SelectData
        Set sd = selMgr.CreateSelectData
        sd.Mark = 1
        Dim it As Variant, ent As SldWorks.Entity
        For Each it In edgeSets(k)
            Set ent = it
            ent.Select4 True, sd
        Next it
        Dim fr As Double
        fr = radii(k) * 0.4
        Dim nf As SldWorks.Feature
        Set nf = swModel.FeatureManager.FeatureFillet3(195, fr / 1000#, 0, 0, Empty, Empty, Empty)
        swModel.ClearSelection2 True
        Dim lbl As String
        lbl = "Rounded ends D" & Format(radii(k) * 2, "0.#") & " (" & edgeSets(k).Count & " ends, R" & Format(fr, "0.0#") & ")"
        If nf Is Nothing Then
            logTxt = logTxt & "SKIPPED  " & lbl & ": fillet could not be created" & vbCrLf
        Else
            swModel.ForceRebuild3 False
            Dim e As String
            e = RebuildErrors()
            If e <> "" Then
                nf.Select2 False, 0
                swModel.EditDelete
                swModel.ForceRebuild3 False
                logTxt = logTxt & "SKIPPED  " & lbl & ": caused errors, removed" & vbCrLf
            Else
                nf.Name = "Rounded ends D" & Format(radii(k) * 2, "0.#")
                logTxt = logTxt & "DONE     " & lbl & vbCrLf
            End If
        End If
    Next k
End Sub

Private Function SizeText() As String
    Dim bx As Variant
    bx = swModel.GetPartBox(True)
    SizeText = Format((bx(3) - bx(0)) * 1000#, "0.0") & " / " & _
               Format((bx(4) - bx(1)) * 1000#, "0.0") & " / " & _
               Format((bx(5) - bx(2)) * 1000#, "0.0")
End Function

Private Function RebuildErrors() As String
    Dim f As SldWorks.Feature, s As String, w As Boolean
    Set f = swModel.FirstFeature
    Do While Not f Is Nothing
        If f.GetErrorCode2(w) <> 0 And Not w Then s = s & "         - " & f.Name & vbCrLf
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
