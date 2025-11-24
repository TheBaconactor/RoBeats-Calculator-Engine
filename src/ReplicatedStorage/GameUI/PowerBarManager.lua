-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:29 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.GameUI.PlayerPlaceSlot)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.PowerBarState)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_7 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v9 = {}
local v_u_10 = Vector2.new(980, 159)
local v_u_11 = Vector2.new(456, 75)
v9.new = function(_, p_u_12) --[[ Name: new ]] --[[ Line: 23 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_5, (copy 4): v_u_2, (copy 5): v_u_10, (copy 6): v_u_11, (copy 7): v_u_6, (copy 8): v_u_7, (copy 9): v_u_1, (copy 10): v_u_8 ]]
    local v_u_13 = v_u_3:SPUIObjectBase()
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = nil
    local v_u_17 = nil
    local v_u_18 = nil
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 37 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_4, (ref 3): v_u_21, (copy 4): v_u_13, (ref 5): v_u_15, (ref 6): v_u_16, (ref 7): v_u_17, (ref 8): v_u_18, (ref 9): v_u_19, (ref 10): v_u_20 ]]
        v_u_14 = game.ReplicatedStorage.WorldUIProto.PowerBar:Clone()
        v_u_14.Parent = v_u_4:get_world_ui_folder()
        v_u_21 = v_u_14.PrimaryPart.SurfaceGui
        v_u_13._native_size = v_u_14.PrimaryPart.Size
        v_u_13._size = v_u_13._native_size
        v_u_15 = v_u_14.PrimaryPart.SurfaceGui.Frame
        v_u_16 = v_u_15.NormalBarFill
        v_u_17 = v_u_15.NormalBarBack
        v_u_18 = v_u_15.FeverBarFill
        v_u_19 = v_u_15.FeverBarBack
        v_u_21.Enabled = false
        v_u_20 = v_u_14.EmitterSurface.ParticleEmitter
        v_u_14.PrimaryPart.SurfaceGui.Frame.ModeDisplay.Visible = false
        v_u_13:set_pct(0)
        v_u_13:update_particle_emitter_params_to_selected_slot()
        v_u_20.Enabled = false
        v_u_17.ImageTransparency = 1
        v_u_16.ImageTransparency = 1
        v_u_19.ImageTransparency = 1
        v_u_18.ImageTransparency = 1
    end;
    v_u_13.update_particle_emitter_params_to_selected_slot = function(_) --[[ Name: update_particle_emitter_params_to_selected_slot ]] --[[ Line: 67 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_12, (ref 3): v_u_20 ]]
        v_u_5:singleton():get_fevericon_for_id(p_u_12:get_game_note_skin_info():get_slot_fevericon_effect_from_setting(p_u_12:get_local_game_slot())):apply_to_emitter(v_u_20)
    end;
    v_u_13.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        v_u_14:Destroy()
        v_u_14 = nil
    end;
    local v_u_22 = -1
    local v_u_23 = Vector2.new(0, 0.05)
    local v_u_24 = Vector2.new(1, 0.95)
    v_u_13.set_pct = function(_, p25) --[[ Name: set_pct ]] --[[ Line: 82 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_23, (copy 3): v_u_24, (ref 4): v_u_22, (ref 5): v_u_16, (ref 6): v_u_10, (ref 7): v_u_11, (ref 8): v_u_18 ]]
        local v26 = v_u_2:YForPointOf2PtLine(v_u_23, v_u_24, p25)
        if v_u_22 ~= v26 then
            v_u_22 = v26
            v_u_16.ImageRectSize = v_u_10 * Vector2.new(v26, 1)
            v_u_16.Size = UDim2.new(0, v_u_11.X * v26, 0, v_u_11.Y)
            v_u_18.ImageRectSize = v_u_16.ImageRectSize
            v_u_18.Size = v_u_16.Size
        end;
    end;
    local v_u_27 = 1
    local v_u_28 = 1
    local function _(p29) --[[ Name: set_normal_bar_transparency ]] --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_16 ]]
        if p29 ~= v_u_17.ImageTransparency then
            v_u_17.ImageTransparency = p29
            v_u_16.ImageTransparency = p29
        end;
    end;
    local function _(p30) --[[ Name: set_fever_transparency ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_18 ]]
        if p30 ~= v_u_19.ImageTransparency then
            v_u_19.ImageTransparency = p30
            v_u_18.ImageTransparency = p30
        end;
    end;
    local function _() --[[ Name: is_powerbar_active ]] --[[ Line: 111 ]]
        --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_6 ]]
        local v31, v32 = p_u_12:es_gamelocal_get_scoremanager():get_score_objs()
        if v_u_6:get_selected_mode() == v_u_6.Compete then
            return v31:is_powerbar_active();
        else
            return v32:is_powerbar_active();
        end;
    end;
    local function _() --[[ Name: get_power_bar_pct ]] --[[ Line: 120 ]]
        --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_6 ]]
        local v33, v34 = p_u_12:es_gamelocal_get_scoremanager():get_score_objs()
        if v_u_6:get_selected_mode() == v_u_6.Compete then
            return v33:get_power_bar_pct();
        else
            return v34:get_power_bar_pct();
        end;
    end;
    local v_u_35 = 1
    local v_u_36 = 1
    v_u_13.update_visual = function(_, p37, _) --[[ Name: update_visual ]] --[[ Line: 131 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_35, (ref 3): v_u_36, (copy 4): p_u_12, (ref 5): v_u_20, (ref 6): v_u_6, (ref 7): v_u_27, (ref 8): v_u_2, (ref 9): v_u_17, (ref 10): v_u_16, (ref 11): v_u_28, (ref 12): v_u_19, (ref 13): v_u_18 ]]
        v_u_21.Enabled = true
        v_u_35 = 1
        v_u_36 = 1
        if p_u_12:es_gamelocal_get_audiomanager():is_playing() == false then
            v_u_20.Enabled = false
        else
            local v38, v39 = p_u_12:es_gamelocal_get_scoremanager():get_score_objs()
            local v40
            if v_u_6:get_selected_mode() == v_u_6.Compete then
                v40 = v38:is_powerbar_active()
            else
                v40 = v39:is_powerbar_active()
            end;
            if v40 == true then
                v_u_36 = 0.1
                v_u_20.Enabled = true
            else
                v_u_20.Enabled = false
                v_u_35 = 0.15
            end;
        end;
        v_u_27 = v_u_2:Expt(v_u_27, v_u_35, v_u_2:NormalizedDefaultExptValueInSeconds(1), p37)
        local v41 = v_u_27
        if v41 ~= v_u_17.ImageTransparency then
            v_u_17.ImageTransparency = v41
            v_u_16.ImageTransparency = v41
        end;
        v_u_28 = v_u_2:Expt(v_u_28, v_u_36, v_u_2:NormalizedDefaultExptValueInSeconds(1), p37)
        local v42 = v_u_28
        if v42 ~= v_u_19.ImageTransparency then
            v_u_19.ImageTransparency = v42
            v_u_18.ImageTransparency = v42
        end;
    end;
    local v_u_43 = v_u_3:cframe_params_default()
    local l__spui_0 = p_u_12._spui
    local v_u_44 = p_u_12._ui_manager:get_decal_ui_manager()
    v_u_13.layout = function(p45) --[[ Name: layout ]] --[[ Line: 167 ]]
        --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_7, (copy 3): v_u_44, (copy 4): l__spui_0, (copy 5): v_u_43, (ref 6): v_u_1, (ref 7): v_u_14 ]]
        local v46 = p_u_12:es_gamelocal_get_tracksystems():get(p_u_12:get_local_game_slot())
        local v47
        if v46 then
            v47 = v46:get_active_note_display_mode() == v_u_7.DecalDown and true or v46:get_active_note_display_mode() == v_u_7.DecalUp
        else
            v47 = false
        end;
        if v47 then
            local _, v48 = v_u_44:get_track_size_and_position()
            v_u_43.PositionNXY:set(v48:get(1) / v_u_1:screen_size().X - p45:get_native_size().Y / l__spui_0:get_size_from_nxy(1, 1).X * 0.5, 0.5)
            v_u_43.OffsetXYZ:from_vector3(p45:anchored_offset(0.5, 0.5))
            v_u_43.LocalRotationOffset:set(0, 0, -90)
        else
            v_u_43.PositionNXY:set(0.5, 1)
            v_u_43.OffsetXYZ:from_vector3(p45:anchored_offset(0.5, 1) + Vector3.new(0, l__spui_0:get_size_from_nxy(0, 0).Y))
            v_u_43.LocalRotationOffset:set(0, 0, 0)
        end;
        local v49, v50 = p45:opt_update_cframe_params(l__spui_0, v_u_43)
        if v49 == true then
            v_u_14:SetPrimaryPartCFrame(v50)
        end;
    end;
    v_u_13.get_native_size = function(p51) --[[ Name: get_native_size ]] --[[ Line: 202 ]]
        return p51._native_size;
    end;
    v_u_13.get_size = function(p52) --[[ Name: get_size ]] --[[ Line: 205 ]]
        return p52._size;
    end;
    v_u_13.set_size = function(p53, p54) --[[ Name: set_size ]] --[[ Line: 208 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        p53._size = p54
        v_u_14.PrimaryPart.Size = Vector3.new(p54.X, p54.Y, 0)
    end;
    local v_u_55 = 0
    local l_GamePowerBar_0 = v_u_8.Test.GamePowerBar
    v_u_8:register_ui_needs_refresh_should_run_test_type(l_GamePowerBar_0)
    v_u_13.update = function(p56, p57, _) --[[ Name: update ]] --[[ Line: 216 ]]
        --[[ Upvalues: (ref 1): v_u_8, (copy 2): l_GamePowerBar_0, (ref 3): v_u_35, (ref 4): v_u_27, (copy 5): p_u_12, (ref 6): v_u_55, (ref 7): v_u_2, (ref 8): v_u_6 ]]
        local v58 = v_u_8:singleton()
        if v58:should_run(l_GamePowerBar_0) == false then
            if v_u_35 ~= v_u_27 then
                p56:update_visual(p57, p_u_12)
            end;
        else
            local v59 = v58:get_test_state(l_GamePowerBar_0):get_dt_scale()
            p56:layout()
            local v60 = v_u_2
            local v61 = v_u_55
            local v62, v63 = p_u_12:es_gamelocal_get_scoremanager():get_score_objs()
            local v64
            if v_u_6:get_selected_mode() == v_u_6.Compete then
                v64 = v62:get_power_bar_pct()
            else
                v64 = v63:get_power_bar_pct()
            end;
            v_u_55 = v60:Expt(v61, v64, v_u_2:NormalizedDefaultExptValueInSeconds(0.45), v59)
            p56:set_pct(v_u_55)
            p56:update_visual(v59, p_u_12)
        end;
    end;
    f_cons()
    return v_u_13;
end;
return v9;
