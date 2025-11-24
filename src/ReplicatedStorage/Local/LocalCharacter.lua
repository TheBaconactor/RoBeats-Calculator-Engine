-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:26 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_6 = require(game.ReplicatedStorage.Avatar.SPAvatarUtil)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.DanceType)
local v_u_9 = require(game.ReplicatedStorage.Shared.GameDanceInfo)
local v_u_10 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_12 = require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Effects.CharacterShineEffect)
local v_u_13 = require(game.ReplicatedStorage.Local.BackupDancer)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
return {
    ["new"] = function(_, p_u_15, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_11, (copy 3): v_u_10, (copy 4): v_u_5, (copy 5): v_u_2, (copy 6): v_u_1, (copy 7): v_u_13, (copy 8): v_u_6, (copy 9): v_u_7, (copy 10): v_u_9, (copy 11): v_u_8, (copy 12): v_u_3, (copy 13): v_u_14, (copy 14): v_u_12 ]]
        local v_u_19 = {}
        v_u_19.get_game_slot = function(_) --[[ Name: get_game_slot ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): p_u_17 ]]
            return p_u_17;
        end;
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = 0
        local v_u_24 = 1
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        local v_u_29 = nil
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = 1
        local v_u_35 = v_u_4:new()
        local v_u_36 = v_u_4:new()
        local v_u_37 = v_u_4:new()
        local v_u_38 = v_u_4:new()
        local v_u_39 = v_u_4:new()
        v_u_19.get_slot = function(_) --[[ Name: get_slot ]] --[[ Line: 55 ]]
            --[[ Upvalues: (copy 1): p_u_17 ]]
            return p_u_17;
        end;
        v_u_19.get_backup_dancers = function(_) --[[ Name: get_backup_dancers ]] --[[ Line: 56 ]]
            --[[ Upvalues: (copy 1): v_u_39 ]]
            return v_u_39;
        end;
        local v_u_40 = v_u_11:new()
        local v_u_41 = true
        v_u_19.get_character_location = function(_) --[[ Name: get_character_location ]] --[[ Line: 62 ]]
            --[[ Upvalues: (copy 1): p_u_15, (copy 2): p_u_17 ]]
            return p_u_15._characters:get_character_location_for_slot(p_u_17);
        end;
        local function _(p42) --[[ Name: backup_dancer_set_anchored ]] --[[ Line: 64 ]]
            --[[ Upvalues: (copy 1): v_u_39 ]]
            for _, v43 in v_u_39:key_itr() do
                v43:set_anchored(p42)
            end;
        end;
        local function f_make_local_clone() --[[ Name: make_local_clone ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_17, (ref 3): v_u_5, (copy 4): p_u_16, (ref 5): v_u_2, (ref 6): v_u_1, (copy 7): v_u_19, (ref 8): v_u_13, (copy 9): p_u_15, (ref 10): v_u_41, (copy 11): p_u_18, (copy 12): v_u_39, (ref 13): v_u_6, (ref 14): v_u_7, (copy 15): v_u_40, (ref 16): v_u_9, (copy 17): v_u_35, (ref 18): v_u_8, (copy 19): v_u_36, (copy 20): v_u_37, (copy 21): v_u_38 ]]
            local v44
            if v_u_10.SwapGameDebugCharacter == true then
                if p_u_17 == 1 then
                    v44 = game.ReplicatedStorage.PlayerSlot1
                elseif p_u_17 == 2 then
                    v44 = game.ReplicatedStorage.PlayerSlot2
                elseif p_u_17 == 3 then
                    v44 = game.ReplicatedStorage.PlayerSlot3
                else
                    v44 = game.ReplicatedStorage.PlayerSlot4
                end;
            else
                v44 = v_u_5:get_character_model_for_playerid(p_u_16)
            end;
            v44.Archivable = true
            local v_u_45 = v44:Clone()
            v_u_45.Name = v_u_2:gen_name(v_u_45.Name)
            if v_u_45 == nil then
                v_u_1:errf("could not load character(game.ReplicatedStorage.CharacterProtos.%d)", p_u_16)
            end;
            local v46 = v_u_45:FindFirstChild("Humanoid")
            if v46 ~= nil then
                for _, v47 in pairs(Enum.HumanoidStateType:GetEnumItems()) do
                    if v47 ~= Enum.HumanoidStateType.None then
                        v46:SetStateEnabled(v47, false)
                    end;
                end;
                v46.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
            end;
            v_u_45.PrimaryPart.Anchored = true
            local function _() --[[ Name: set_clone_position ]] --[[ Line: 105 ]]
                --[[ Upvalues: (copy 1): v_u_45, (ref 2): v_u_19, (ref 3): v_u_13, (ref 4): p_u_15 ]]
                v_u_45:SetPrimaryPartCFrame(v_u_19:get_character_location())
                v_u_13:set_backup_dancer_positions(p_u_15, v_u_19)
            end;
            if v_u_41 then
                v_u_13:create_backup_dancers(p_u_15, v_u_19, p_u_18)
            end;
            for _, v48 in v_u_39:key_itr() do
                v48:set_anchored(true)
            end;
            v_u_45.Parent = v_u_5:get_local_elements_folder()
            v_u_45:SetPrimaryPartCFrame(v_u_19:get_character_location())
            v_u_13:set_backup_dancer_positions(p_u_15, v_u_19)
            v_u_6:character_modify_with_equipped_data(v_u_45, v44, p_u_18._equipped, function() --[[ Line: 117 ]]
                --[[ Upvalues: (copy 1): v_u_45 ]]
                v_u_45.PrimaryPart.Anchored = true
            end)
            local function _(p49, p50) --[[ Name: backup_dancer_preload_dance_type ]] --[[ Line: 121 ]]
                --[[ Upvalues: (ref 1): v_u_39 ]]
                for _, v51 in v_u_39:key_itr() do
                    v51:preload_dance_type_animation(p49, p50)
                end;
            end;
            local function f_fill_anim_list_with_dancetype(p_u_52, p_u_53) --[[ Name: fill_anim_list_with_dancetype ]] --[[ Line: 127 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): p_u_17, (ref 3): v_u_7, (ref 4): v_u_2, (copy 5): v_u_45, (ref 6): v_u_40, (ref 7): v_u_39, (ref 8): v_u_9 ]]
                local v54 = p_u_15:get_game_dance_info():get_danceids_for_slot_and_type(p_u_17, p_u_53)
                if v54:count() > 0 then
                    for v55 = 1, v54:count() do
                        local v_u_56 = v_u_7:singleton():get_dance_animation_for_id(v54:get(v55))
                        v_u_2:ptry(function() --[[ Line: 132 ]]
                            --[[ Upvalues: (ref 1): v_u_45, (copy 2): v_u_56, (copy 3): p_u_52, (ref 4): v_u_40, (copy 5): p_u_53, (ref 6): v_u_39 ]]
                            local v57 = v_u_45.Humanoid:LoadAnimation(v_u_56)
                            p_u_52:push_back(v57)
                            v_u_40:add(v57, v_u_56)
                            local v58 = p_u_53
                            local v59 = v_u_56
                            for _, v60 in v_u_39:key_itr() do
                                v60:preload_dance_type_animation(v58, v59)
                            end;
                        end)
                    end;
                else
                    local v_u_61 = v_u_7:singleton():get_dance_animation_for_id(v_u_9:get_default_dance_id())
                    v_u_2:ptry(function() --[[ Line: 141 ]]
                        --[[ Upvalues: (ref 1): v_u_45, (copy 2): v_u_61, (copy 3): p_u_52, (ref 4): v_u_40, (copy 5): p_u_53, (ref 6): v_u_39 ]]
                        local v62 = v_u_45.Humanoid:LoadAnimation(v_u_61)
                        p_u_52:push_back(v62)
                        v_u_40:add(v62, v_u_61)
                        local v63 = p_u_53
                        local v64 = v_u_61
                        for _, v65 in v_u_39:key_itr() do
                            v65:preload_dance_type_animation(v63, v64)
                        end;
                    end)
                end;
            end;
            f_fill_anim_list_with_dancetype(v_u_35, v_u_8.Idle)
            f_fill_anim_list_with_dancetype(v_u_36, v_u_8.OnMiss)
            f_fill_anim_list_with_dancetype(v_u_37, v_u_8.Standard)
            f_fill_anim_list_with_dancetype(v_u_38, v_u_8.Combo)
            return v_u_45;
        end;
        local function f_backup_dancer_play_current_anim() --[[ Name: backup_dancer_play_current_anim ]] --[[ Line: 159 ]]
            --[[ Upvalues: (copy 1): v_u_40, (ref 2): v_u_33, (copy 3): v_u_39 ]]
            if v_u_40:contains(v_u_33) then
                local v66 = v_u_40:get(v_u_33)
                for _, v67 in v_u_39:key_itr() do
                    v67:play_animation_assetid(v66)
                end;
            end;
        end;
        local function _(p68) --[[ Name: play_anim ]] --[[ Line: 168 ]]
            --[[ Upvalues: (ref 1): v_u_33, (copy 2): f_backup_dancer_play_current_anim ]]
            if p68 ~= nil then
                if p68 ~= v_u_33 then
                    if v_u_33 ~= nil then
                        v_u_33:Stop()
                    end;
                    v_u_33 = p68
                    v_u_33:Play()
                    f_backup_dancer_play_current_anim()
                end;
            end;
        end;
        local function f_update_visual(_) --[[ Name: update_visual ]] --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): v_u_22, (copy 2): p_u_15, (ref 3): v_u_2, (ref 4): v_u_21, (ref 5): v_u_3, (ref 6): v_u_24 ]]
            local l_magnitude_0 = (game.Workspace.CurrentCamera.CFrame.p - v_u_22.PrimaryPart.Position).magnitude
            if p_u_15:show_fullscreen_mobile_ui() then
                v_u_22.PrimaryPart.CFrame = v_u_2:lookat_camera_cframe(v_u_21.Position + Vector3.new(0, v_u_3:YForPointOf2PtLine(Vector2.new(0, 2.5), Vector2.new(70, 5), l_magnitude_0), 0), p_u_15._spui)
            else
                v_u_22.PrimaryPart.CFrame = v_u_2:lookat_camera_cframe(v_u_21.Position + Vector3.new(0, v_u_3:YForPointOf2PtLine(Vector2.new(0, 3.75), Vector2.new(70, 5), l_magnitude_0), 0), p_u_15._spui)
            end;
            local v69 = v_u_3:YForPointOf2PtLine(Vector2.new(0, 4.5), Vector2.new(70, 15), l_magnitude_0) * v_u_24
            v_u_2:set_size(v_u_22.PrimaryPart, v69, v69 * 0.3, 0)
        end;
        local v_u_70 = -1
        local function f_set_nametag_alpha(p71) --[[ Name: set_nametag_alpha ]] --[[ Line: 207 ]]
            --[[ Upvalues: (ref 1): v_u_70, (ref 2): v_u_25, (ref 3): v_u_2, (ref 4): v_u_26, (ref 5): v_u_28, (ref 6): v_u_29, (ref 7): v_u_27, (ref 8): v_u_31, (ref 9): v_u_22 ]]
            if p71 ~= v_u_70 then
                v_u_70 = p71
                v_u_25.TextTransparency = v_u_2:tra(p71)
                v_u_25.TextStrokeTransparency = v_u_2:tra(p71)
                v_u_26.TextTransparency = v_u_2:tra(p71)
                v_u_26.TextStrokeTransparency = v_u_2:tra(p71)
                v_u_28.TextTransparency = v_u_2:tra(p71)
                v_u_28.TextStrokeTransparency = v_u_2:tra(p71)
                v_u_29.TextTransparency = v_u_2:tra(p71)
                v_u_29.TextStrokeTransparency = v_u_2:tra(p71)
                v_u_27.ImageTransparency = v_u_2:tra(p71)
                v_u_31.ImageTransparency = v_u_2:tra(p71)
                v_u_22.MainSurface.SurfaceGui.Frame.Frame.ProfileIcon.ImageTransparency = v_u_2:tra(p71)
                v_u_22.MainSurface.SurfaceGui.Frame.Frame.ProfileIconBack.ImageTransparency = v_u_2:tra(p71)
            end;
        end;
        v_u_19.cons = function(p72) --[[ Name: cons ]] --[[ Line: 228 ]]
            --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_41, (copy 3): p_u_17, (ref 4): v_u_20, (copy 5): f_make_local_clone, (ref 6): v_u_21, (copy 7): v_u_35, (ref 8): v_u_33, (copy 9): f_backup_dancer_play_current_anim, (ref 10): v_u_34, (ref 11): v_u_22, (ref 12): v_u_10, (ref 13): v_u_25, (ref 14): v_u_27, (ref 15): v_u_28, (ref 16): v_u_29, (ref 17): v_u_26, (ref 18): v_u_31, (copy 19): p_u_18, (ref 20): v_u_14, (ref 21): v_u_32, (ref 22): v_u_30, (copy 23): f_update_visual, (copy 24): f_set_nametag_alpha, (ref 25): v_u_23 ]]
            local v73 = true
            local v74 = p_u_15:is_spectate()
            local v75 = not p_u_15._characters:should_show_characters()
            local v76
            if p_u_15.is_preview_game == nil then
                v76 = false
            else
                v76 = p_u_15:is_preview_game()
            end;
            if v76 then
                v_u_41 = false
            elseif v74 then
                if v75 then
                    v73 = false
                    v_u_41 = false
                end;
            else
                local v77 = p_u_17 == p_u_15:get_local_game_slot()
                if p_u_15:show_fullscreen_mobile_ui() and v77 ~= true then
                    v73 = false
                    v_u_41 = false
                end;
                if v75 then
                    v73 = false
                    v_u_41 = false
                end;
                if v77 ~= true then
                    v_u_41 = false
                end;
            end;
            v_u_20 = f_make_local_clone()
            v_u_21 = v_u_20.Humanoid.RootPart
            if v73 ~= true then
                p72:set_visible(false)
            end;
            local v78 = v_u_35:get(1)
            if v78 ~= nil and v78 ~= v_u_33 then
                if v_u_33 ~= nil then
                    v_u_33:Stop()
                end;
                v_u_33 = v78
                v_u_33:Play()
                f_backup_dancer_play_current_anim()
            end;
            v_u_34 = 0
            v_u_22 = game.ReplicatedStorage.ElementProtos.NametagProtoV2:Clone()
            if p_u_15:show_fullscreen_mobile_ui() then
                v_u_22.MainSurface.SurfaceGui.Enabled = false
            end;
            if v_u_10.HideOverheadNametag == true then
                v_u_22.MainSurface.SurfaceGui.Enabled = false
            end;
            v_u_22.Parent = v_u_20
            local l_Frame_0 = v_u_22.MainSurface.SurfaceGui.Frame
            v_u_25 = l_Frame_0.PlaceDisplay
            v_u_27 = l_Frame_0.CrownIcon
            v_u_28 = l_Frame_0.Frame.LikeIcon
            v_u_29 = l_Frame_0.Frame.LikeDisplay
            v_u_26 = l_Frame_0.NameDisplay
            v_u_31 = l_Frame_0.Frame.PlayerFeverIconDisplay
            if v_u_10.DebugUseTestName == true then
                v_u_26.Text = v_u_10.DebugTestName
            else
                v_u_26.Text = p_u_18._name
            end;
            local v79 = v_u_14:singleton():get_title_for_id(p_u_18._title_id)
            if v79 then
                l_Frame_0.NameDisplay.TextColor3 = v79:get_color()
            end;
            v_u_31.Image = p_u_18._icon
            v_u_25.Text = ""
            v_u_27.Visible = false
            v_u_28.Visible = false
            v_u_29.Text = ""
            v_u_32 = l_Frame_0.Frame
            v_u_30 = v_u_32.ProfileIcon
            v_u_30.Image = string.format("https://www.roblox.com/headshot-thumbnail/image?userId=%d&width=150&height=150&format=png", p_u_18._id)
            f_update_visual(p_u_15)
            f_set_nametag_alpha(v_u_23)
        end;
        local v_u_80 = true
        v_u_19.get_visible = function(_) --[[ Name: get_visible ]] --[[ Line: 322 ]]
            --[[ Upvalues: (ref 1): v_u_80 ]]
            return v_u_80;
        end;
        v_u_19.set_visible = function(_, p81) --[[ Name: set_visible ]] --[[ Line: 323 ]]
            --[[ Upvalues: (ref 1): v_u_80, (ref 2): v_u_20, (ref 3): v_u_5 ]]
            v_u_80 = p81
            if v_u_20 then
                if p81 then
                    v_u_20.Parent = v_u_5:get_local_elements_folder()
                    return;
                end;
                v_u_20.Parent = nil
            end;
        end;
        v_u_19.play_anim_from_current_tier = function(_) --[[ Name: play_anim_from_current_tier ]] --[[ Line: 334 ]]
            --[[ Upvalues: (ref 1): v_u_34, (copy 2): v_u_38, (ref 3): v_u_33, (copy 4): f_backup_dancer_play_current_anim, (copy 5): v_u_37, (copy 6): v_u_36, (copy 7): v_u_35 ]]
            if v_u_34 == 3 then
                local v82 = v_u_38:random()
                if v82 == nil then
                    return;
                end;
                if v82 ~= v_u_33 then
                    if v_u_33 ~= nil then
                        v_u_33:Stop()
                    end;
                    v_u_33 = v82
                    v_u_33:Play()
                    f_backup_dancer_play_current_anim()
                    return;
                end;
            elseif v_u_34 == 2 then
                local v83 = v_u_37:random()
                if v83 == nil then
                    return;
                end;
                if v83 ~= v_u_33 then
                    if v_u_33 ~= nil then
                        v_u_33:Stop()
                    end;
                    v_u_33 = v83
                    v_u_33:Play()
                    f_backup_dancer_play_current_anim()
                    return;
                end;
            elseif v_u_34 == 1 then
                local v84 = v_u_36:random()
                if v84 == nil then
                    return;
                end;
                if v84 ~= v_u_33 then
                    if v_u_33 ~= nil then
                        v_u_33:Stop()
                    end;
                    v_u_33 = v84
                    v_u_33:Play()
                    f_backup_dancer_play_current_anim()
                    return;
                end;
            else
                local v85 = v_u_35:random()
                if v85 == nil then
                    return;
                end;
                if v85 ~= v_u_33 then
                    if v_u_33 ~= nil then
                        v_u_33:Stop()
                    end;
                    v_u_33 = v85
                    v_u_33:Play()
                    f_backup_dancer_play_current_anim()
                end;
            end;
        end;
        local v_u_86 = 0
        local v_u_87 = 0
        local v_u_88 = 0
        v_u_19.update = function(p89, p90, _) --[[ Name: update ]] --[[ Line: 353 ]]
            --[[ Upvalues: (ref 1): v_u_20, (copy 2): p_u_15, (ref 3): v_u_12, (copy 4): p_u_18, (copy 5): p_u_17, (ref 6): v_u_86, (ref 7): v_u_87, (ref 8): v_u_34, (ref 9): v_u_88, (ref 10): v_u_3, (ref 11): v_u_25, (ref 12): v_u_27, (ref 13): v_u_28, (ref 14): v_u_29, (ref 15): v_u_24, (ref 16): v_u_23, (copy 17): f_set_nametag_alpha, (copy 18): f_update_visual ]]
            if v_u_20 ~= nil and v_u_20.PrimaryPart ~= nil then
                if v_u_20.PrimaryPart.Anchored == true then
                    local v91 = p_u_15:es_gamelocal_get_scoremanager():get_local_note_count()
                    local _, _, _, v92 = p_u_15:es_gamelocal_get_scoremanager():get_end_records()
                    local v93 = false
                    local v94 = v_u_12:get_server_game_instance_player_chain(p_u_18)
                    local v95 = v_u_12:get_server_game_instance_player_powerbar_active(p_u_18)
                    local v96
                    if p_u_15:get_local_game_slot() == p_u_17 then
                        v96 = v_u_86 < v92 and true or v93
                        v_u_86 = v92
                    else
                        v96 = v94 < v_u_87 and true or v93
                        v_u_87 = v_u_12:get_server_game_instance_player_chain(p_u_18)
                    end;
                    local v97 = v_u_34
                    local v98 = false
                    if v91 == 0 then
                        v97 = 0
                        v_u_88 = 0
                    elseif v96 or v94 == 0 then
                        v97 = 1
                        v_u_88 = 0
                    else
                        v_u_88 = v_u_88 + v_u_3:TimescaleToDeltaTime(p90)
                        if v_u_34 == 0 then
                            v_u_88 = 0
                            v97 = 2
                            v98 = true
                        elseif v_u_34 == 1 and v_u_88 >= 1.5 then
                            v97 = 2
                            v_u_88 = 0
                            v98 = true
                        elseif v_u_34 == 2 and v_u_88 >= 5 then
                            v_u_88 = 0
                            v98 = true
                        elseif v_u_34 == 2 and v95 == true then
                            v_u_88 = 0
                            v97 = 3
                            v98 = true
                        elseif v_u_34 == 3 and v_u_88 >= 6 then
                            v_u_88 = 0
                            v98 = true
                        elseif v_u_34 == 3 and v95 == false then
                            v_u_88 = 0
                            v97 = 2
                            v98 = true
                        end;
                    end;
                    if v97 == v_u_34 then
                        if v98 then
                            p89:play_anim_from_current_tier()
                        end;
                    else
                        v_u_34 = v97
                        p89:play_anim_from_current_tier()
                    end;
                else
                    v_u_20.PrimaryPart.Anchored = true
                end;
                local v99 = p_u_15._players:get_slot_place(p_u_15, p_u_17)
                local v100 = false
                if v99 == 2 then
                    v_u_25.Text = "2nd"
                elseif v99 == 3 then
                    v_u_25.Text = "3rd"
                elseif v99 == 4 then
                    v_u_25.Text = "4th"
                else
                    v_u_25.Text = "1st"
                    v100 = true
                end;
                v_u_27.Visible = v100
                if p_u_18._like_count > 0 then
                    v_u_28.Visible = true
                    v_u_29.Visible = true
                    v_u_29.Text = string.format("%d", p_u_18._like_count)
                else
                    v_u_28.Visible = false
                    v_u_29.Visible = false
                end;
                v_u_24 = v_u_3:expt_sec(v_u_24, 0.95, 0.5, p90)
                v_u_23 = v_u_3:expt_sec(v_u_23, 0.9, 0.5, p90)
                f_set_nametag_alpha(v_u_23)
                f_update_visual(p_u_15, p90)
            end;
        end;
        v_u_19.set_paused = function(_, p101) --[[ Name: set_paused ]] --[[ Line: 466 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            if v_u_33 == nil then
                return;
            elseif p101 == true then
                v_u_33:AdjustSpeed(0)
            else
                v_u_33:AdjustSpeed(1)
            end;
        end;
        v_u_19.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 475 ]]
            --[[ Upvalues: (copy 1): v_u_39, (ref 2): v_u_22, (ref 3): v_u_20, (ref 4): v_u_21 ]]
            for _, v102 in v_u_39:key_itr() do
                v102:cleanup()
            end;
            v_u_39:clear()
            v_u_22:Destroy()
            v_u_22 = nil
            v_u_20:Destroy()
            v_u_20 = nil
            v_u_21 = nil
        end;
        v_u_19:cons()
        return v_u_19;
    end
};
