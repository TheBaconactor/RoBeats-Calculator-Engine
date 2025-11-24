-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_8 = require(game.ReplicatedStorage.GameStage.Util.AudioSampler)
local v_u_9 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_10 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_13, (ref 4): v_u_14, (ref 5): v_u_15 ]]
    v_u_11 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
    v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_13 = require(game.ReplicatedStorage.Local.CrowdManager)
    v_u_14 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_15 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
local v16 = {}
local function f_create_trigger_button_asset(p_u_17, p_u_18, p19, p20) --[[ Name: create_trigger_button_asset ]] --[[ Line: 32 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_7, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_5, (copy 6): v_u_6 ]]
    local v_u_21 = p20:Clone()
    local v22 = v_u_1.TriggerButtonAsset:new(p_u_17, p_u_18, p19, v_u_21)
    local v_u_23 = 1
    local v_u_24 = v_u_7:new()
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local function _() --[[ Name: cons ]] --[[ Line: 42 ]]
        --[[ Upvalues: (ref 1): v_u_27, (copy 2): v_u_21, (ref 3): v_u_25, (ref 4): v_u_26, (copy 5): v_u_24 ]]
        v_u_27 = v_u_21.MainGlow
        v_u_25 = v_u_21.InteriorCircle
        v_u_26 = v_u_21.ExteriorCircle
        v_u_24:push_back_table_list({
            v_u_21.FrameLower,
            v_u_21.FrameUpper,
            v_u_21.ExteriorCircle.Glow,
            v_u_21.MainGlow
        })
    end;
    local v_u_28 = v_u_4:get_default_base_color():to_color3()
    local v_u_29 = v_u_4:get_default_fever_color():to_color3()
    v_u_2:get_base_fn(v22, "set_game_noteskin_colors")
    v22.set_game_noteskin_colors = function(_, p30, p31) --[[ Name: set_game_noteskin_colors ]] --[[ Line: 57 ]]
        --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_29 ]]
        v_u_28 = p30
        v_u_29 = p31
    end;
    local v_u_32 = false
    v_u_2:get_base_fn(v22, "on_press")
    v22.on_press = function(_) --[[ Name: on_press ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_32 ]]
        v_u_23 = 0.75
        v_u_32 = true
    end;
    v_u_2:get_base_fn(v22, "on_release")
    v22.on_release = function(_) --[[ Name: on_release ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_32 ]]
        v_u_23 = 1
        v_u_32 = false
    end;
    local v_u_33 = 0
    local v_u_34 = 0
    local v_u_35 = 0
    local v_u_36 = 0
    v_u_2:get_base_fn(v22, "update")
    v22.update = function(p37, p38) --[[ Name: update ]] --[[ Line: 83 ]]
        --[[ Upvalues: (copy 1): p_u_18, (copy 2): p_u_17, (ref 3): v_u_32, (ref 4): v_u_33, (ref 5): v_u_25, (ref 6): v_u_34, (ref 7): v_u_5, (ref 8): v_u_35, (ref 9): v_u_26, (ref 10): v_u_36, (ref 11): v_u_27, (ref 12): v_u_23, (ref 13): v_u_28, (ref 14): v_u_6, (ref 15): v_u_29, (copy 16): v_u_24 ]]
        if p_u_18 == p_u_17:get_local_game_slot() then
            if v_u_32 then
                if v_u_33 > 1 then
                    v_u_33 = v_u_33 - 1
                    v_u_25:SetPrimaryPartCFrame(CFrame.new(p37:get_initial_cframe().p) * CFrame.Angles(0, v_u_34, 0))
                    v_u_34 = (v_u_34 - v_u_5:sec_to_tick(0.3) * 1) % 180
                end;
                v_u_33 = v_u_33 + p38
                if v_u_35 > 1 then
                    v_u_35 = v_u_35 - 1
                    v_u_26:SetPrimaryPartCFrame(CFrame.new(p37:get_initial_cframe().p) * CFrame.Angles(0, v_u_36, 0))
                    v_u_36 = (v_u_36 + v_u_5:sec_to_tick(0.7) * 1) % 180
                end;
                v_u_35 = v_u_35 + p38
            end;
            v_u_27.Transparency = v_u_5:Expt(v_u_27.Transparency, v_u_23, v_u_5:NormalizedDefaultExptValueInSeconds(0.45), p38)
            local v39 = v_u_28
            if v_u_6:get_server_game_instance_player_powerbar_active(p_u_17._players._slots:get(p_u_18)) then
                v39 = v_u_29
            end;
            for _, v40 in v_u_24:key_itr() do
                v40.Color = v39
            end;
        end;
    end;
    v_u_27 = v_u_21.MainGlow
    local _ = v_u_21.InteriorCircle
    local _ = v_u_21.ExteriorCircle
    v_u_24:push_back_table_list({
        v_u_21.FrameLower,
        v_u_21.FrameUpper,
        v_u_21.ExteriorCircle.Glow,
        v_u_21.MainGlow
    })
    return v22;
end;
v16.new = function(_) --[[ Name: new ]] --[[ Line: 128 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_9, (copy 4): v_u_10, (copy 5): v_u_7, (ref 6): v_u_12, (ref 7): v_u_14, (copy 8): v_u_8, (copy 9): v_u_3, (copy 10): v_u_5, (copy 11): f_create_trigger_button_asset ]]
    local v41 = v_u_1:new()
    v_u_2:get_base_fn(v41, "get_name")
    v41.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 132 ]]
        return "Rhythm Galaxies";
    end;
    v_u_2:get_base_fn(v41, "get_icon")
    v41.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 134 ]]
        return "rbxassetid://9354214197";
    end;
    local v_u_42 = nil
    v41.load_stage = function(_, p_u_43) --[[ Name: load_stage ]] --[[ Line: 137 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_42 ]]
        v_u_9:singleton():load_model_category(v_u_10.GameStage.MCCustomServerStage, v_u_10.Category.GameStage, function(p44) --[[ Line: 138 ]]
            --[[ Upvalues: (ref 1): v_u_42, (copy 2): p_u_43 ]]
            v_u_42 = p44
            p_u_43()
        end)
    end;
    local v_u_45 = nil
    local v_u_46 = nil
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = v_u_7:new()
    local v_u_50 = nil
    v_u_2:get_base_fn(v41, "setup_stage")
    v41.setup_stage = function(p51, p52) --[[ Name: setup_stage ]] --[[ Line: 153 ]]
        --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_42, (ref 3): v_u_46, (ref 4): v_u_47, (ref 5): v_u_7, (copy 6): v_u_49, (ref 7): v_u_12, (ref 8): v_u_50, (ref 9): v_u_14, (ref 10): v_u_48, (ref 11): v_u_8 ]]
        v_u_45 = v_u_42.Stage
        v_u_46 = v_u_42.CharacterShineProto
        v_u_47 = v_u_42.TriggerButtonProto
        local function f_add_audio_visualizer_bar_list(p53) --[[ Name: add_audio_visualizer_bar_list ]] --[[ Line: 158 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            local v54 = v_u_7:new()
            v54:push_back_table_list({
                p53.Bar12,
                p53.Bar11,
                p53.Bar10,
                p53.Bar9,
                p53.Bar8,
                p53.Bar7,
                p53.Bar6,
                p53.Bar5,
                p53.Bar4,
                p53.Bar3,
                p53.Bar2,
                p53.Bar1
            })
            return v54;
        end;
        v_u_49:push_back((f_add_audio_visualizer_bar_list(v_u_45.AudioVisualizerLeft)))
        v_u_49:push_back((f_add_audio_visualizer_bar_list(v_u_45.AudioVisualizerRight)))
        v_u_12:get_game_lighting().ClockTime = 0
        p51:on_switch_focus_slot(p52)
        v_u_45.Parent = v_u_12:get_local_elements_folder()
        v_u_47.Parent = nil
        v_u_50 = v_u_14:new(v_u_46, Vector3.new(0, -3.5, 0))
        v_u_48 = v_u_8:new(p52)
        v_u_48:set_sample_count(v_u_49:get(1):count())
        for _, v55 in v_u_49:key_itr() do
            for _, v56 in v55:key_itr() do
                v56.Size = Vector3.new(0.1, 0, 0.1)
            end;
        end;
    end;
    v_u_2:get_base_fn(v41, "on_switch_focus_slot")
    v41.on_switch_focus_slot = function(_, p57) --[[ Name: on_switch_focus_slot ]] --[[ Line: 201 ]]
        --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_3 ]]
        v_u_45:SetPrimaryPartCFrame(CFrame.new(v_u_3:get_world_center_position(), v_u_3:slot_to_world_position(p57:get_local_game_slot())))
    end;
    v_u_2:get_base_fn(v41, "create_shine_for_slot_at_cframe")
    v41.create_shine_for_slot_at_cframe = function(_, p58, p59, p60) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 209 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        v_u_50:create_shine_for_slot_at_cframe(p58, p59, p60)
    end;
    v_u_2:get_base_fn(v41, "teardown_stage")
    v41.teardown_stage = function(_, p61) --[[ Name: teardown_stage ]] --[[ Line: 214 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_42, (ref 3): v_u_45, (ref 4): v_u_46, (ref 5): v_u_47 ]]
        v_u_50:teardown(p61)
        v_u_42:Destroy()
        v_u_45:Destroy()
        v_u_46:Destroy()
        v_u_47:Destroy()
    end;
    v_u_2:get_base_fn(v41, "game_update")
    v41.game_update = function(_, p62, p63) --[[ Name: game_update ]] --[[ Line: 223 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_48, (copy 3): v_u_49, (ref 4): v_u_5 ]]
        v_u_50:update(p62, p63)
        v_u_48:update(p62)
        local v64 = v_u_48:get_samples()
        for _, v65 in v_u_49:key_itr() do
            for v66 = 1, v65:count() do
                local v67 = v65:get(v66)
                if v66 <= v64:count() then
                    v67.Size = Vector3.new(0.1, v_u_5:YForPointOf2PtLineP1P2X(0, 0, 600, 10, (v64:get(v66))), 0.1)
                else
                    v67.Size = Vector3.new(0.1, 1, 0.1)
                end;
            end;
        end;
    end;
    v_u_2:get_base_fn(v41, "create_trigger_button_asset")
    v41.create_trigger_button_asset = function(_, p68, p69, p70) --[[ Name: create_trigger_button_asset ]] --[[ Line: 246 ]]
        --[[ Upvalues: (ref 1): f_create_trigger_button_asset, (ref 2): v_u_47 ]]
        return f_create_trigger_button_asset(p68, p69, p70, v_u_47);
    end;
    return v41;
end;
return v16;
