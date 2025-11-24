-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_5 = require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = require(game.ReplicatedStorage.Shared.RotatingCFrameObject)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_11 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_12 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_14, (ref 3): v_u_15, (ref 4): v_u_16, (ref 5): v_u_17 ]]
    v_u_13 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
    v_u_14 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_15 = require(game.ReplicatedStorage.Local.CrowdManager)
    v_u_16 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_17 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
local v18 = {}
local function f_create_trigger_button_asset(p_u_19, p_u_20, p21, p22) --[[ Name: create_trigger_button_asset ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_8, (copy 3): v_u_9, (copy 4): v_u_2, (copy 5): v_u_5, (copy 6): v_u_6, (copy 7): v_u_7 ]]
    local v_u_23 = p22:Clone()
    local v24 = v_u_1.TriggerButtonAsset:new(p_u_19, p_u_20, p21, v_u_23)
    local v_u_25 = 1
    local v_u_26 = v_u_8:new()
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 45 ]]
        --[[ Upvalues: (ref 1): v_u_29, (copy 2): v_u_23, (ref 3): v_u_28, (ref 4): v_u_9, (ref 5): v_u_27, (copy 6): v_u_26 ]]
        v_u_29 = v_u_23.MainGlow
        local l_Cover_0 = v_u_23.ExteriorCircle.Cover
        local l_Glow_0 = v_u_23.ExteriorCircle.Glow
        v_u_28 = v_u_9:new(l_Cover_0, nil, function(p30) --[[ Line: 54 ]]
            --[[ Upvalues: (copy 1): l_Cover_0, (copy 2): l_Glow_0 ]]
            l_Cover_0.CFrame = p30
            l_Glow_0.CFrame = p30
        end):set_rotate_time_sec(3.5999999999999996)
        local l_Lower_0 = v_u_23.InteriorCircle.Lower
        local l_Upper_0 = v_u_23.InteriorCircle.Upper
        v_u_27 = v_u_9:new(l_Lower_0, nil, function(p31) --[[ Line: 68 ]]
            --[[ Upvalues: (copy 1): l_Lower_0, (copy 2): l_Upper_0 ]]
            l_Lower_0.CFrame = p31
            l_Upper_0.CFrame = p31
        end):set_rotate_time_sec(8.399999999999999)
        v_u_26:push_back_table_list({
            v_u_23.FrameLower,
            v_u_23.FrameUpper,
            v_u_23.ExteriorCircle.Glow,
            v_u_23.MainGlow
        })
    end;
    local v_u_32 = v_u_2:get_base_fn(v24, "set_cframe")
    v24.set_cframe = function(p33, p34) --[[ Name: set_cframe ]] --[[ Line: 85 ]]
        --[[ Upvalues: (copy 1): v_u_32, (ref 2): v_u_28, (ref 3): v_u_27 ]]
        v_u_32(p33, p34)
        v_u_28:set_initial_cframe_position(p33:get_initial_cframe().p)
        v_u_27:set_initial_cframe_position(p33:get_initial_cframe().p)
    end;
    local v_u_35 = v_u_5:get_default_base_color():to_color3()
    local v_u_36 = v_u_5:get_default_fever_color():to_color3()
    v_u_2:get_base_fn(v24, "set_game_noteskin_colors")
    v24.set_game_noteskin_colors = function(_, p37, p38) --[[ Name: set_game_noteskin_colors ]] --[[ Line: 94 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_36 ]]
        v_u_35 = p37
        v_u_36 = p38
    end;
    local v_u_39 = false
    v_u_2:get_base_fn(v24, "on_press")
    v24.on_press = function(_) --[[ Name: on_press ]] --[[ Line: 102 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_39 ]]
        v_u_25 = 0.75
        v_u_39 = true
    end;
    v_u_2:get_base_fn(v24, "on_release")
    v24.on_release = function(_) --[[ Name: on_release ]] --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_39 ]]
        v_u_25 = 1
        v_u_39 = false
    end;
    v_u_2:get_base_fn(v24, "update")
    v24.update = function(_, p40) --[[ Name: update ]] --[[ Line: 114 ]]
        --[[ Upvalues: (copy 1): p_u_20, (copy 2): p_u_19, (ref 3): v_u_39, (ref 4): v_u_27, (ref 5): v_u_28, (ref 6): v_u_29, (ref 7): v_u_6, (ref 8): v_u_25, (ref 9): v_u_35, (ref 10): v_u_7, (ref 11): v_u_36, (copy 12): v_u_26 ]]
        if p_u_20 == p_u_19:get_local_game_slot() then
            if v_u_39 then
                v_u_27:update_obj_cframe(p40)
                v_u_28:update_obj_cframe(p40)
            end;
            v_u_29.Transparency = v_u_6:Expt(v_u_29.Transparency, v_u_25, v_u_6:NormalizedDefaultExptValueInSeconds(0.45), p40)
            local v41 = v_u_35
            if v_u_7:get_server_game_instance_player_powerbar_active(p_u_19._players._slots:get(p_u_20)) then
                v41 = v_u_36
            end;
            for _, v42 in v_u_26:key_itr() do
                v42.Color = v41
            end;
        end;
    end;
    f_cons()
    return v24;
end;
v18.new = function(_) --[[ Name: new ]] --[[ Line: 142 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_11, (copy 4): v_u_12, (copy 5): v_u_8, (copy 6): v_u_7, (ref 7): v_u_14, (copy 8): v_u_10, (copy 9): v_u_6, (copy 10): v_u_3, (copy 11): v_u_9, (ref 12): v_u_16, (copy 13): v_u_4, (copy 14): f_create_trigger_button_asset ]]
    local v43 = v_u_1:new()
    v_u_2:get_base_fn(v43, "get_name")
    v43.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 146 ]]
        return "Dimetric Daybreak";
    end;
    v_u_2:get_base_fn(v43, "get_icon")
    v43.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 148 ]]
        return "rbxassetid://9659667325";
    end;
    local v_u_44 = nil
    v43.load_stage = function(_, p_u_45) --[[ Name: load_stage ]] --[[ Line: 151 ]]
        --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_44 ]]
        v_u_11:singleton():load_model_category(v_u_12.GameStage.HexagonSunsetStage, v_u_12.Category.GameStage, function(p46) --[[ Line: 152 ]]
            --[[ Upvalues: (ref 1): v_u_44, (copy 2): p_u_45 ]]
            v_u_44 = p46
            p_u_45()
        end)
    end;
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = nil
    local v_u_50 = nil
    local v_u_51 = nil
    local v_u_52 = nil
    local v_u_53 = v_u_8:new()
    local function f_update_color(p54) --[[ Name: update_color ]] --[[ Line: 165 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_53 ]]
        local v55 = p54:get_game_note_skin_info()
        local v56 = v55:get_slot_basecolor_list(p54:get_local_game_slot())
        local v57 = v55:get_slot_fevercolor_list(p54:get_local_game_slot())
        local v58
        if v_u_7:get_server_game_instance_player_powerbar_active(p54._players._slots:get(p54:get_local_game_slot())) then
            v58 = v57:get(1):to_color3()
            v57:get(2):to_color3()
            v57:get(3):to_color3()
            v57:get(4):to_color3()
        else
            v58 = v56:get(1):to_color3()
            v56:get(2):to_color3()
            v56:get(3):to_color3()
            v56:get(4):to_color3()
        end;
        for _, v59 in v_u_53:key_itr() do
            v59.Color = v58
        end;
    end;
    local v_u_60 = nil
    v_u_2:get_base_fn(v43, "setup_stage")
    v43.setup_stage = function(p61, p62) --[[ Name: setup_stage ]] --[[ Line: 188 ]]
        --[[ Upvalues: (ref 1): v_u_47, (ref 2): v_u_44, (ref 3): v_u_48, (ref 4): v_u_49, (ref 5): v_u_14, (ref 6): v_u_10, (ref 7): v_u_6, (ref 8): v_u_3, (ref 9): v_u_50, (ref 10): v_u_9, (ref 11): v_u_51, (ref 12): v_u_52, (ref 13): v_u_60, (ref 14): v_u_16, (copy 15): v_u_53, (copy 16): f_update_color ]]
        v_u_47 = v_u_44.Stage
        v_u_48 = v_u_44.CharacterShineProto
        v_u_49 = v_u_44.TriggerButtonProto
        p61:on_switch_focus_slot(p62)
        local v63 = v_u_14:get_game_sky()
        v63.SkyboxBk = "rbxassetid://600830446"
        v63.SkyboxDn = "rbxassetid://600831635"
        v63.SkyboxFt = "rbxassetid://600832720"
        v63.SkyboxLf = "rbxassetid://600886090"
        v63.SkyboxRt = "rbxassetid://600833862"
        v63.SkyboxUp = "rbxassetid://600835177"
        v_u_47.Parent = v_u_14:get_local_elements_folder()
        v_u_49.Parent = nil
        local v64 = v_u_10:singleton():get_difficulty_for_key(p62:es_gamelocal_get_audiomanager():get_song_key())
        local v65 = v_u_6:YForPointOf2PtLineP1P2X(5, 84, 30, 42, v_u_3:clamp(v64, 5, 30))
        local v66 = v_u_6:YForPointOf2PtLineP1P2X(5, 156, 30, 78, v_u_3:clamp(v64, 5, 30))
        v_u_50 = v_u_9:new(v_u_47.MovingParts.HexGlow):set_rotate_time_sec(v65)
        v_u_51 = v_u_9:new(v_u_47.MovingParts.HexCover):set_rotate_time_sec(v65)
        v_u_52 = v_u_9:new(v_u_47.MovingParts.HexOuter):set_rotation_axis(Vector3.new(0, -1, 0)):set_rotate_time_sec(v66)
        v_u_60 = v_u_16:new(v_u_48, Vector3.new(0, -3.5, 0))
        v_u_53:clear()
        v_u_53:push_back_table_list({ v_u_47.MovingParts.HexGlow, v_u_47.MovingParts.GlowRing })
        f_update_color(p62)
    end;
    v_u_2:get_base_fn(v43, "on_switch_focus_slot")
    v43.on_switch_focus_slot = function(_, p67) --[[ Name: on_switch_focus_slot ]] --[[ Line: 230 ]]
        --[[ Upvalues: (ref 1): v_u_47, (ref 2): v_u_4 ]]
        v_u_47:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p67:get_local_game_slot())))
    end;
    v_u_2:get_base_fn(v43, "create_shine_for_slot_at_cframe")
    v43.create_shine_for_slot_at_cframe = function(_, p68, p69, p70) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 238 ]]
        --[[ Upvalues: (ref 1): v_u_60 ]]
        v_u_60:create_shine_for_slot_at_cframe(p68, p69, p70)
    end;
    v_u_2:get_base_fn(v43, "teardown_stage")
    v43.teardown_stage = function(_, p71) --[[ Name: teardown_stage ]] --[[ Line: 243 ]]
        --[[ Upvalues: (ref 1): v_u_60, (ref 2): v_u_44, (ref 3): v_u_47, (ref 4): v_u_48, (ref 5): v_u_49, (ref 6): v_u_50, (ref 7): v_u_51, (ref 8): v_u_52, (copy 9): v_u_53 ]]
        v_u_60:teardown(p71)
        v_u_44:Destroy()
        v_u_47:Destroy()
        v_u_48:Destroy()
        v_u_49:Destroy()
        v_u_50 = nil
        v_u_51 = nil
        v_u_52 = nil
        v_u_53:clear()
    end;
    v_u_2:get_base_fn(v43, "game_update")
    v43.game_update = function(_, p72, p73) --[[ Name: game_update ]] --[[ Line: 256 ]]
        --[[ Upvalues: (ref 1): v_u_60, (ref 2): v_u_50, (ref 3): v_u_51, (ref 4): v_u_52, (copy 5): f_update_color ]]
        v_u_60:update(p72, p73)
        v_u_50:update_obj_cframe(p72)
        v_u_51:update_obj_cframe(p72)
        v_u_52:update_obj_cframe(p72)
        f_update_color(p73)
    end;
    v_u_2:get_base_fn(v43, "create_trigger_button_asset")
    v43.create_trigger_button_asset = function(_, p74, p75, p76) --[[ Name: create_trigger_button_asset ]] --[[ Line: 265 ]]
        --[[ Upvalues: (ref 1): f_create_trigger_button_asset, (ref 2): v_u_49 ]]
        return f_create_trigger_button_asset(p74, p75, p76, v_u_49);
    end;
    v_u_2:get_base_fn(v43, "should_do_game_start_zoom_in_effect")
    v43.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 270 ]]
        return true, 36.5, 18.900000000000002, 0.75;
    end;
    return v43;
end;
return v18;
