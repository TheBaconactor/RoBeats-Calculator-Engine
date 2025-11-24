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
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_10 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_11 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_12 = nil
local v_u_13 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 19 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13 ]]
    v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_13 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
end)
local v14 = {}
local function f_create_trigger_button_asset(p_u_15, p_u_16, p17, p18) --[[ Name: create_trigger_button_asset ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_8, (copy 3): v_u_5, (copy 4): v_u_2, (copy 5): v_u_6, (copy 6): v_u_3, (copy 7): v_u_7 ]]
    local v_u_19 = p18:Clone()
    local v20 = v_u_1.TriggerButtonAsset:new(p_u_15, p_u_16, p17, v_u_19)
    local v_u_21 = 0.25
    local v_u_22 = v_u_8:new()
    local v_u_23 = nil
    local function _() --[[ Name: cons ]] --[[ Line: 38 ]]
        --[[ Upvalues: (ref 1): v_u_23, (copy 2): v_u_19, (copy 3): v_u_22 ]]
        v_u_23 = v_u_19.ButtonHighlight
        v_u_22:push_back_table_list({ v_u_19.ButtonHighlight, v_u_19.ButtonDetails })
    end;
    local v_u_24 = v_u_5:get_default_base_color():to_color3()
    local v_u_25 = v_u_5:get_default_fever_color():to_color3()
    v_u_2:get_base_fn(v20, "set_game_noteskin_colors")
    v20.set_game_noteskin_colors = function(_, p26, p27) --[[ Name: set_game_noteskin_colors ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25 ]]
        v_u_24 = p26
        v_u_25 = p27
    end;
    v_u_2:get_base_fn(v20, "on_press")
    v20.on_press = function(_) --[[ Name: on_press ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21 = 0.75
    end;
    v_u_2:get_base_fn(v20, "on_release")
    v20.on_release = function(_) --[[ Name: on_release ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21 = 0.25
    end;
    v_u_2:get_base_fn(v20, "update")
    v20.update = function(_, p28) --[[ Name: update ]] --[[ Line: 65 ]]
        --[[ Upvalues: (copy 1): p_u_16, (copy 2): p_u_15, (ref 3): v_u_23, (ref 4): v_u_6, (ref 5): v_u_3, (ref 6): v_u_21, (ref 7): v_u_24, (ref 8): v_u_7, (ref 9): v_u_25, (copy 10): v_u_22 ]]
        if p_u_16 == p_u_15:get_local_game_slot() then
            v_u_23.Transparency = v_u_6:Expt(v_u_23.Transparency, v_u_3:tra(v_u_21), v_u_6:NormalizedDefaultExptValueInSeconds(0.45), p28)
            local v29 = v_u_24
            if v_u_7:get_server_game_instance_player_powerbar_active(p_u_15._players._slots:get(p_u_16)) then
                v29 = v_u_25
            end;
            for _, v30 in v_u_22:key_itr() do
                v30.Color = v29
            end;
        end;
    end;
    v_u_23 = v_u_19.ButtonHighlight
    v_u_22:push_back_table_list({ v_u_19.ButtonHighlight, v_u_19.ButtonDetails })
    return v20;
end;
v14.new = function(_) --[[ Name: new ]] --[[ Line: 88 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_10, (copy 4): v_u_11, (ref 5): v_u_12, (copy 6): v_u_9, (copy 7): v_u_6, (copy 8): v_u_3, (ref 9): v_u_13, (copy 10): v_u_8, (copy 11): v_u_4, (copy 12): v_u_7, (copy 13): f_create_trigger_button_asset ]]
    local v31 = v_u_1:new()
    v_u_2:get_base_fn(v31, "get_name")
    v31.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 92 ]]
        return "Inter-Planetary Orbit (SDVB)";
    end;
    v_u_2:get_base_fn(v31, "get_icon")
    v31.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 94 ]]
        return "rbxassetid://9719075459";
    end;
    local v_u_32 = nil
    v31.load_stage = function(_, p_u_33) --[[ Name: load_stage ]] --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_32 ]]
        v_u_10:singleton():load_model_category(v_u_11.GameStage.SDVBBackgroundSpaceStation, v_u_11.Category.GameStage, function(p34) --[[ Line: 98 ]]
            --[[ Upvalues: (ref 1): v_u_32, (copy 2): p_u_33 ]]
            v_u_32 = p34
            p_u_33()
        end)
    end;
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = nil
    local v_u_38 = nil
    local v_u_39 = nil
    local v_u_40 = 0
    local v_u_41 = 2
    local function _(p42) --[[ Name: update_background_frame_visual ]] --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_39 ]]
        v_u_38:SetPrimaryPartCFrame(v_u_39 + v_u_39.LookVector * (p42 * 291))
    end;
    local v_u_43 = nil
    local v_u_44 = nil
    local v_u_45 = nil
    local v_u_46 = nil
    local v_u_47 = 0
    local v_u_48 = nil
    local v_u_49 = nil
    local v_u_50 = nil
    v_u_2:get_base_fn(v31, "setup_stage")
    v31.setup_stage = function(p51, p52) --[[ Name: setup_stage ]] --[[ Line: 124 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_32, (ref 3): v_u_36, (ref 4): v_u_37, (ref 5): v_u_12, (ref 6): v_u_38, (ref 7): v_u_39, (ref 8): v_u_9, (ref 9): v_u_41, (ref 10): v_u_6, (ref 11): v_u_3, (ref 12): v_u_43, (ref 13): v_u_44, (ref 14): v_u_45, (ref 15): v_u_46, (ref 16): v_u_50, (ref 17): v_u_13, (ref 18): v_u_48, (ref 19): v_u_8, (ref 20): v_u_49 ]]
        v_u_35 = v_u_32.Stage
        v_u_36 = v_u_32.CharacterShineProto
        v_u_37 = v_u_32.TriggerButtonProto
        local v53 = v_u_12:get_game_sky()
        v53.SkyboxDn = "rbxassetid://9582244789"
        v53.SkyboxUp = "rbxassetid://9582245125"
        v53.SkyboxBk = "rbxassetid://9582245019"
        v53.SkyboxFt = "rbxassetid://9582245019"
        v53.SkyboxLf = "rbxassetid://9582245019"
        v53.SkyboxRt = "rbxassetid://9582245019"
        v_u_38 = v_u_35.BackgroundFrames
        v_u_39 = v_u_38.PrimaryPart.CFrame
        v_u_41 = v_u_6:YForPointOf2PtLineP1P2X(5, 3, 30, 1, v_u_3:clamp(v_u_9:singleton():get_difficulty_for_key(p52:es_gamelocal_get_audiomanager():get_song_key()), 5, 30))
        p51:on_switch_focus_slot(p52)
        v_u_35.Parent = v_u_12:get_local_elements_folder()
        v_u_37.Parent = nil
        v_u_43 = v_u_35.CenterEmitter.BillboardGui.Frame.Glow1
        v_u_44 = v_u_35.CenterEmitter.BillboardGui.Frame.Glow2
        v_u_45 = v_u_35.CenterEmitter.BillboardGui.Frame.Glow3
        v_u_46 = v_u_35.CenterEmitter.BillboardGui.Frame.Glow4
        v_u_50 = v_u_13:new(v_u_36, Vector3.new(0, -3.5, 0))
        v_u_48 = v_u_8:new()
        if p52:show_fullscreen_mobile_ui() then
            v_u_35.ButtonPanelPC.Parent = nil
            v_u_35.TrackHighlightPC.Parent = nil
            v_u_48:push_back(v_u_35.ButtonPanelMobile.BackGlow)
            v_u_49 = v_u_3:get_list_of_children_of_classname(v_u_35.ButtonPanelMobile.BackGlow, "ParticleEmitter")
        else
            v_u_35.ButtonPanelMobile.Parent = nil
            v_u_35.TrackHighlightMobile.Parent = nil
            v_u_48:push_back(v_u_35.ButtonPanelPC.BackGlow)
            v_u_49 = v_u_3:get_list_of_children_of_classname(v_u_35.ButtonPanelPC.BackGlow, "ParticleEmitter")
        end;
        for _, v54 in v_u_48:key_itr() do
            v54.Transparency = 0
        end;
        for _, v55 in v_u_49:key_itr() do
            v55.Enabled = true
            v55.Rate = 0
        end;
    end;
    v_u_2:get_base_fn(v31, "on_switch_focus_slot")
    v31.on_switch_focus_slot = function(_, p56) --[[ Name: on_switch_focus_slot ]] --[[ Line: 185 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_39, (ref 3): v_u_35, (ref 4): v_u_4 ]]
        v_u_38:SetPrimaryPartCFrame(v_u_39 + v_u_39.LookVector * 0)
        v_u_35:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p56:get_local_game_slot())))
        v_u_39 = v_u_38.PrimaryPart.CFrame
    end;
    v_u_2:get_base_fn(v31, "create_shine_for_slot_at_cframe")
    v31.create_shine_for_slot_at_cframe = function(_, p57, p58, p59) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 195 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        v_u_50:create_shine_for_slot_at_cframe(p57, p58, p59)
    end;
    v_u_2:get_base_fn(v31, "teardown_stage")
    v31.teardown_stage = function(_, p60) --[[ Name: teardown_stage ]] --[[ Line: 200 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_32, (ref 3): v_u_35, (ref 4): v_u_36, (ref 5): v_u_37, (ref 6): v_u_48, (ref 7): v_u_49 ]]
        v_u_50:teardown(p60)
        v_u_32:Destroy()
        v_u_35:Destroy()
        v_u_36:Destroy()
        v_u_37:Destroy()
        v_u_48 = nil
        v_u_49 = nil
    end;
    v_u_2:get_base_fn(v31, "game_update")
    v31.game_update = function(_, p61, p62) --[[ Name: game_update ]] --[[ Line: 211 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_47, (ref 3): v_u_6, (ref 4): v_u_43, (ref 5): v_u_3, (ref 6): v_u_44, (ref 7): v_u_45, (ref 8): v_u_46, (ref 9): v_u_40, (ref 10): v_u_41, (ref 11): v_u_38, (ref 12): v_u_39, (ref 13): v_u_7, (ref 14): v_u_48, (ref 15): v_u_49 ]]
        v_u_50:update(p61, p62)
        v_u_47 = v_u_6:IncrementWrap(v_u_47, v_u_6:SecondsToTick(1) * p61, 1)
        local v63 = v_u_6:YForPointOf2PtLineP1P2X(-1, 0.45, 1, 0.85, (math.sin(v_u_47 * 2 * 3.141592653589793)))
        v_u_43.ImageTransparency = v_u_3:tra(v63)
        v_u_44.ImageTransparency = v_u_3:tra(v63 * 0.5)
        v_u_45.ImageTransparency = v_u_3:tra(v63 * 0.25)
        v_u_46.ImageTransparency = v_u_3:tra(v63 * 0.25)
        v_u_40 = v_u_6:IncrementWrap(v_u_40, v_u_6:SecondsToTick(v_u_41) * p61, 1)
        v_u_38:SetPrimaryPartCFrame(v_u_39 + v_u_39.LookVector * (v_u_40 * 291))
        local v64 = v_u_7:get_server_game_instance_player_powerbar_active(p62._players._slots:get(p62:get_local_game_slot()))
        for _, v65 in v_u_48:key_itr() do
            if v64 then
                v65.Transparency = 0.25
            else
                v65.Transparency = 0.75
            end;
        end;
        for _, v66 in v_u_49:key_itr() do
            if v64 then
                v66.Rate = 40
            else
                v66.Rate = 5
            end;
        end;
    end;
    v_u_2:get_base_fn(v31, "create_trigger_button_asset")
    v31.create_trigger_button_asset = function(_, p67, p68, p69) --[[ Name: create_trigger_button_asset ]] --[[ Line: 253 ]]
        --[[ Upvalues: (ref 1): f_create_trigger_button_asset, (ref 2): v_u_37 ]]
        return f_create_trigger_button_asset(p67, p68, p69, v_u_37);
    end;
    return v31;
end;
return v14;
