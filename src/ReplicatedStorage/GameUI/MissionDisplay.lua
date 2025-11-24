-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_7 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
local v_u_8 = require(game.ReplicatedStorage.Shared.MissionType)
require(game.ReplicatedStorage.Shared.LVector3)
local v_u_9 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_10 = require(game.ReplicatedStorage.Shared.SPRange)
local v_u_11 = require(game.ReplicatedStorage.Shared.AudioRank)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_13 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_14 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_15 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_16 = require(game.ReplicatedStorage.Shared.Mission.MissionActiveData)
local v_u_17 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_18 = require(game.ReplicatedStorage.Shared.Mission.ScaledScoreMissionUtil)
local v_u_19 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_20 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v21 = {}
local v_u_22 = v3:new():add_set_from_table_list({
    v_u_8.Score,
    v_u_8.PointTotal,
    v_u_8.Rank,
    v_u_8.WinMatch,
    v_u_8.CompleteMatch,
    v_u_8.ScaledScore,
    v_u_8.NoMiss
})
v21.new = function(_, p_u_23) --[[ Name: new ]] --[[ Line: 39 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_7, (copy 3): v_u_16, (copy 4): v_u_10, (copy 5): v_u_15, (copy 6): v_u_17, (copy 7): v_u_5, (copy 8): v_u_1, (copy 9): v_u_19, (copy 10): v_u_13, (copy 11): v_u_12, (copy 12): v_u_14, (copy 13): v_u_6, (copy 14): v_u_22, (copy 15): v_u_20, (copy 16): v_u_8, (copy 17): v_u_11, (copy 18): v_u_18, (copy 19): v_u_9, (copy 20): v_u_2 ]]
    local v_u_24 = v_u_4:SPUIObjectBase()
    local v_u_25 = nil
    local v_u_26 = Vector2.new(437, 24)
    local v_u_27 = Vector2.new(444, 30)
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local function _(p36) --[[ Name: set_surfacegui_enabled ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_25, (ref 3): v_u_35 ]]
        if v_u_34 == nil then
            v_u_34 = v_u_25.PrimaryPart.SurfaceGui
        end;
        if p36 ~= v_u_35 then
            v_u_35 = p36
            v_u_34.Enabled = p36
        end;
    end;
    local v_u_37 = false
    local l_Daily_0 = v_u_7.Daily
    local v_u_38 = v_u_16.MissionData:new(-1)
    local v_u_39 = v_u_10:new(1, -0.7)
    local v_u_40 = v_u_39:min()
    local function _() --[[ Name: display_mode_is_2d ]] --[[ Line: 71 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_15 ]]
        local v41 = p_u_23:es_gamelocal_get_tracksystems():get(p_u_23:get_local_game_slot())
        return v41 and v41:get_active_note_display_mode() ~= v_u_15.Default and true or false;
    end;
    local function _() --[[ Name: get_player_count ]] --[[ Line: 80 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_17 ]]
        local l__slots_0 = p_u_23._players._slots
        local v42 = 0
        for v43 = 1, v_u_17.SLOT_MAX do
            if l__slots_0:contains(v43) then
                v42 = v42 + 1
            end;
        end;
        return v42;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 91 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_5, (copy 3): p_u_23, (ref 4): v_u_15, (ref 5): v_u_39, (ref 6): v_u_10, (ref 7): v_u_40, (copy 8): v_u_24, (ref 9): v_u_28, (ref 10): v_u_29, (ref 11): v_u_27, (ref 12): v_u_26, (ref 13): v_u_30, (ref 14): v_u_31, (ref 15): v_u_32, (ref 16): v_u_33, (ref 17): v_u_1, (ref 18): v_u_34, (ref 19): v_u_35, (ref 20): v_u_17, (ref 21): v_u_19, (ref 22): v_u_13, (ref 23): v_u_12, (ref 24): v_u_14, (ref 25): v_u_37, (ref 26): v_u_38, (ref 27): v_u_7, (ref 28): v_u_6, (ref 29): v_u_16, (ref 30): v_u_22, (ref 31): l_Daily_0 ]]
        v_u_25 = game.ReplicatedStorage.WorldUIProto.MissionProgressBar:Clone()
        v_u_25.Parent = v_u_5:get_world_ui_folder()
        if not p_u_23:show_fullscreen_mobile_ui() then
            local v44 = p_u_23:es_gamelocal_get_tracksystems():get(p_u_23:get_local_game_slot())
            if not v44 or v44:get_active_note_display_mode() == v_u_15.Default then
                -- ::l6:: (Possible bug with goto)
                v_u_24._native_size = v_u_25.PrimaryPart.Size
                v_u_24._size = v_u_24._native_size
                local l_Frame_0 = v_u_25.PrimaryPart.SurfaceGui.Frame
                v_u_28 = l_Frame_0.BarFillMain
                v_u_29 = l_Frame_0.BarFillAlt
                v_u_29.Visible = false
                v_u_27 = Vector2.new(v_u_28.Size.X.Offset, v_u_28.Size.Y.Offset)
                v_u_26 = v_u_28.ImageRectSize
                v_u_30 = l_Frame_0.MissionCompleteSection
                v_u_30.Visible = false
                v_u_31 = l_Frame_0.RewardLevelSection
                v_u_31.Visible = false
                v_u_32 = l_Frame_0.BarText
                v_u_32.Text = ""
                v_u_33 = l_Frame_0.DifficultyIcon
                v_u_33.Image = v_u_1:transparent_assetid()
                if v_u_34 == nil then
                    v_u_34 = v_u_25.PrimaryPart.SurfaceGui
                end;
                if v_u_35 ~= false then
                    v_u_35 = false
                    v_u_34.Enabled = false
                end;
                v_u_24:set_pct(0)
                v_u_24:set_alpha(0)
                local l__slots_1 = p_u_23._players._slots
                local v_u_45 = 0
                for v46 = 1, v_u_17.SLOT_MAX do
                    if l__slots_1:contains(v46) then
                        v_u_45 = v_u_45 + 1
                    end;
                end;
                if p_u_23._player_settings_manager:get_key(v_u_19.Key.ShowGameMissionDisplay) ~= false then
                    local v_u_47 = p_u_23._player_blob_manager:get_player_blob()
                    if p_u_23:is_networked() == true and (p_u_23._player_blob_manager:is_synced() and v_u_47 ~= nil) then
                        if v_u_13:test_enum_member(p_u_23:get_event_info(), v_u_12.EventMission) == true then
                            local v48 = p_u_23:es_gamelocal_get_audiomanager():get_song_key()
                            local v49, v50, v51, _, _ = v_u_12:get_event_mission_display_info(p_u_23)
                            if v49 ~= v_u_14:invalid_songkey() and v48 == v49 then
                                v_u_37 = true
                                v_u_38:set_target_song(v49)
                                v_u_38:set_type(v50)
                                v_u_38:set_count(v51)
                                v_u_38:set_players_required(v51)
                                if v_u_34 == nil then
                                    v_u_34 = v_u_25.PrimaryPart.SurfaceGui
                                end;
                                if v_u_35 ~= true then
                                    v_u_35 = true
                                    v_u_34.Enabled = true
                                end;
                            end;
                        end;
                        if v_u_37 ~= true then
                            local v_u_52 = p_u_23._player_blob_manager:get_server_mission_data()
                            for _, v_u_53 in v_u_7:get_all():key_itr() do
                                v_u_6:playerblob_missiondata_available_foreach(v_u_47, v_u_52, v_u_53, function(p54) --[[ Line: 154 ]]
                                    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_37, (ref 3): v_u_22, (ref 4): v_u_6, (copy 5): v_u_47, (copy 6): v_u_52, (copy 7): v_u_53, (copy 8): v_u_45, (ref 9): p_u_23, (ref 10): l_Daily_0, (ref 11): v_u_38, (ref 12): v_u_33, (ref 13): v_u_34, (ref 14): v_u_25, (ref 15): v_u_35 ]]
                                    local v55 = v_u_16.MissionData:from_table(p54)
                                    if v_u_37 ~= true and (v_u_22:contains(v55:get_type()) and (v_u_6:playerblob_missiondata_missionid_is_completeable(v_u_47, v_u_52, v_u_53, v55:get_id()) ~= true and (v_u_45 >= v55:get_players_required() and (v55:has_target_song() and v55:get_target_song() == p_u_23:es_gamelocal_get_audiomanager():get_song_key())))) then
                                        v_u_37 = true
                                        l_Daily_0 = v_u_53
                                        v_u_38 = v55
                                        v_u_6:render_difficulty_image(v_u_33, v55:get_difficulty())
                                        if v_u_34 == nil then
                                            v_u_34 = v_u_25.PrimaryPart.SurfaceGui
                                        end;
                                        if v_u_35 ~= true then
                                            v_u_35 = true
                                            v_u_34.Enabled = true
                                        end;
                                    end;
                                    if v_u_37 then
                                        return true;
                                    end;
                                end)
                            end;
                            if v_u_37 ~= true then
                                for _, v_u_56 in v_u_7:get_all():key_itr() do
                                    v_u_6:playerblob_missiondata_available_foreach(v_u_47, v_u_52, v_u_56, function(p57) --[[ Line: 181 ]]
                                        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_37, (ref 3): v_u_22, (ref 4): v_u_6, (copy 5): v_u_47, (copy 6): v_u_52, (copy 7): v_u_56, (copy 8): v_u_45, (ref 9): l_Daily_0, (ref 10): v_u_38, (ref 11): v_u_33, (ref 12): v_u_34, (ref 13): v_u_25, (ref 14): v_u_35 ]]
                                        local v58 = v_u_16.MissionData:from_table(p57)
                                        if v_u_37 ~= true and (v_u_22:contains(v58:get_type()) and (v_u_6:playerblob_missiondata_missionid_is_completeable(v_u_47, v_u_52, v_u_56, v58:get_id()) ~= true and (v_u_45 >= v58:get_players_required() and v58:has_target_song() ~= true))) then
                                            v_u_37 = true
                                            l_Daily_0 = v_u_56
                                            v_u_38 = v58
                                            v_u_6:render_difficulty_image(v_u_33, v58:get_difficulty())
                                            if v_u_34 == nil then
                                                v_u_34 = v_u_25.PrimaryPart.SurfaceGui
                                            end;
                                            if v_u_35 ~= true then
                                                v_u_35 = true
                                                v_u_34.Enabled = true
                                            end;
                                        end;
                                        if v_u_37 then
                                            return true;
                                        end;
                                    end)
                                end;
                            end;
                        end;
                    end;
                end;
            end;
        end;
        v_u_39 = v_u_10:new(1, -0.4)
        v_u_40 = v_u_39:min()
        break;
    end;
    v_u_24.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 210 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        v_u_25:Destroy()
        v_u_25 = nil
    end;
    local v_u_59 = -1
    v_u_24.set_pct = function(_, p60) --[[ Name: set_pct ]] --[[ Line: 216 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_59, (ref 3): v_u_28, (ref 4): v_u_26, (ref 5): v_u_27 ]]
        local v61 = v_u_1:clamp(p60, 0, 1)
        if v_u_59 ~= v61 then
            v_u_59 = v61
            v_u_28.ImageRectSize = v_u_26 * Vector2.new(v61, 1)
            v_u_28.Size = UDim2.new(0, v_u_27.X * v61, 0, v_u_27.Y)
        end;
    end;
    local v_u_62 = -1
    v_u_24.set_alpha = function(_, p63) --[[ Name: set_alpha ]] --[[ Line: 227 ]]
        --[[ Upvalues: (ref 1): v_u_62, (ref 2): v_u_1, (ref 3): v_u_25 ]]
        if v_u_62 ~= p63 then
            v_u_62 = p63
            v_u_1:r_set_alpha(v_u_25, v_u_62)
        end;
    end;
    local v_u_64 = 0
    local l_GameMissionBar_0 = v_u_20.Test.GameMissionBar
    v_u_20:register_ui_needs_refresh_should_run_test_type(l_GameMissionBar_0)
    v_u_24.update = function(p65, _, _) --[[ Name: update ]] --[[ Line: 238 ]]
        --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_38, (ref 3): v_u_20, (copy 4): l_GameMissionBar_0, (copy 5): p_u_23, (ref 6): v_u_17, (ref 7): v_u_34, (ref 8): v_u_25, (ref 9): v_u_35, (ref 10): v_u_31, (ref 11): v_u_8, (ref 12): v_u_32, (ref 13): v_u_1, (ref 14): v_u_11, (ref 15): v_u_6, (ref 16): l_Daily_0, (ref 17): v_u_18, (ref 18): v_u_30, (ref 19): v_u_9, (ref 20): v_u_39, (ref 21): v_u_40, (ref 22): v_u_2, (ref 23): v_u_64, (ref 24): v_u_62 ]]
        if v_u_37 == true and v_u_38 ~= nil then
            local v66 = v_u_20:singleton()
            if v66:should_run(l_GameMissionBar_0) == false then
                return;
            else
                local v67 = v66:get_test_state(l_GameMissionBar_0):get_dt_scale()
                local l__slots_2 = p_u_23._players._slots
                local v68 = 0
                for v69 = 1, v_u_17.SLOT_MAX do
                    if l__slots_2:contains(v69) then
                        v68 = v68 + 1
                    end;
                end;
                if v68 < v_u_38:get_players_required() then
                    v_u_37 = false
                    if v_u_34 == nil then
                        v_u_34 = v_u_25.PrimaryPart.SurfaceGui
                    end;
                    if v_u_35 ~= false then
                        v_u_35 = false
                        v_u_34.Enabled = false
                    end;
                else
                    v_u_31.Visible = false
                    local v70 = false
                    local v71 = p_u_23._player_blob_manager:get_player_blob()
                    local v72 = 0.8
                    local v73 = 0
                    if v_u_38:get_type() == v_u_8.Score then
                        v73 = p_u_23:es_gamelocal_get_scoremanager():get_score() / v_u_38:get_count()
                        v_u_32.Text = string.format("Score: %s / %s", v_u_1:comma_value(p_u_23:es_gamelocal_get_scoremanager():get_score()), v_u_1:comma_value(v_u_38:get_count()))
                    elseif v_u_38:get_type() == v_u_8.Rank then
                        local v74 = p_u_23:es_gamelocal_get_scoremanager():get_accuracy()
                        local v75 = v_u_11:index_to_rank_value(v_u_38:get_count())
                        v73 = v74 / v_u_11:rank_value_to_accuracy(v75)
                        v_u_32.Text = string.format("Grade: %s", v_u_11:get_rank_value_name(v75))
                    elseif v_u_38:get_type() == v_u_8.PointTotal then
                        local l__slots_3 = p_u_23._players._slots
                        local v76 = 0
                        for v77 = 1, 4 do
                            if l__slots_3:contains(v77) then
                                v76 = v76 + l__slots_3:get(v77)._score
                            end;
                        end;
                        v_u_32.Text = string.format("Total Score: %s / %s", v_u_1:comma_value(v76), v_u_1:comma_value(v_u_38:get_count()))
                        v73 = v76 / v_u_38:get_count()
                    elseif v_u_38:get_type() == v_u_8.WinMatch then
                        local v78 = v_u_6:playerblob_missionid_get_count(v71, l_Daily_0, v_u_38:get_id())
                        v73 = v78 / v_u_38:get_count()
                        v_u_32.Text = string.format("Win Match: %d / %d", v78, v_u_38:get_count())
                    elseif v_u_38:get_type() == v_u_8.CompleteMatch then
                        v73 = p_u_23:es_gamelocal_get_audiomanager():get_current_time_ms() / p_u_23:es_gamelocal_get_audiomanager():get_song_length_ms()
                        local v79 = v_u_6:playerblob_missionid_get_count(v71, l_Daily_0, v_u_38:get_id())
                        if v_u_38:has_target_song() == true then
                            v_u_32.Text = string.format("Complete this song: %d / %d", v79, v_u_38:get_count())
                        else
                            v_u_32.Text = string.format("Complete any song: %d / %d", v79, v_u_38:get_count())
                        end;
                    elseif v_u_38:get_type() == v_u_8.ScaledScore then
                        local v80 = p_u_23:es_gamelocal_get_scoremanager():get_accuracy()
                        local v81 = v_u_18:mission_difficulty_to_required_accuracy(v_u_38:get_difficulty())
                        if v80 < v81 then
                            v_u_32.Text = string.format("Complete: %.2f%%", v80 / v81 * 100)
                            v73 = v80 / v81
                            v_u_30.Visible = false
                        else
                            v73 = 1
                            v70 = true
                        end;
                    elseif v_u_38:get_type() == v_u_8.NoMiss then
                        local _, _, _, v82, _ = p_u_23:es_gamelocal_get_scoremanager():get_matchmode_score_obj():get_stat_counts()
                        if v82 <= 0 then
                            v_u_32.Text = "Complete this song with no misses!"
                            v73 = 1
                        else
                            v70 = true
                        end;
                    end;
                    if v73 >= 1 then
                        v_u_30.Visible = true
                    else
                        v_u_30.Visible = false
                    end;
                    local v83 = v_u_1:clamp(v73, 0, 1)
                    if p_u_23:get_current_mode() == v_u_9.Game then
                        local v84
                        if v70 then
                            v84 = v_u_39:min()
                        else
                            v84 = v_u_39:max()
                        end;
                        v_u_40 = v_u_2:Expt(v_u_40, v84, v_u_2:NormalizedDefaultExptValueInSeconds(1), v67)
                    else
                        v72 = 0
                    end;
                    v_u_64 = v_u_2:Expt(v_u_64, v83, v_u_2:NormalizedDefaultExptValueInSeconds(0.45), v67)
                    p65:set_pct(v_u_64)
                    p65:set_alpha((v_u_2:Expt(v_u_62, v72, v_u_2:NormalizedDefaultExptValueInSeconds(1), v67)))
                    p65:layout()
                end;
            end;
        else
            return;
        end;
    end;
    local v_u_85 = v_u_4:cframe_params_default()
    v_u_24.layout = function(p86) --[[ Name: layout ]] --[[ Line: 377 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_15, (copy 3): v_u_85, (ref 4): v_u_40, (ref 5): v_u_25 ]]
        local l__spui_0 = p_u_23._spui
        if not p_u_23:show_fullscreen_mobile_ui() then
            local v87 = p_u_23:es_gamelocal_get_tracksystems():get(p_u_23:get_local_game_slot())
            if not v87 or v87:get_active_note_display_mode() == v_u_15.Default then
                l__spui_0:uiobj_rescale_to_max_nxy(p86, 0.35, 0.25, 1)
                v_u_85.PositionNXY:set(0.5, 0)
                v_u_85.OffsetXYZ:from_vector3(p86:anchored_offset(0.5, v_u_40))
                break;
            end;
        end;
        l__spui_0:uiobj_rescale_to_max_nxy(p86, 0.25, 0.25, 1)
        v_u_85.PositionNXY:set(1, 0)
        v_u_85.OffsetXYZ:from_vector3(p86:anchored_offset(1.05, v_u_40))
        -- ::l7:: (Possible bug with goto)
        local v88, v89 = p86:opt_update_cframe_params(l__spui_0, v_u_85)
        if v88 == true then
            v_u_25:SetPrimaryPartCFrame(v89)
        end;
    end;
    v_u_24.get_native_size = function(p90) --[[ Name: get_native_size ]] --[[ Line: 396 ]]
        return p90._native_size;
    end;
    v_u_24.get_size = function(p91) --[[ Name: get_size ]] --[[ Line: 399 ]]
        return p91._size;
    end;
    v_u_24.set_size = function(p92, p93) --[[ Name: set_size ]] --[[ Line: 402 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        p92._size = p93
        v_u_25.PrimaryPart.Size = Vector3.new(p93.X, p93.Y, 0)
    end;
    f_cons()
    return v_u_24;
end;
return v21;
