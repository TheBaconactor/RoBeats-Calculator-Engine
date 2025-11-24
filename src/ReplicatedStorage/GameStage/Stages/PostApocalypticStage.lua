-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_8 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11 ]]
    v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_10 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_11 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_8, (copy 5): v_u_5, (copy 6): v_u_6, (ref 7): v_u_9, (ref 8): v_u_10, (copy 9): v_u_3, (copy 10): v_u_4 ]]
        local v12 = v_u_1:new()
        v_u_2:get_base_fn(v12, "get_name")
        v12.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 33 ]]
            return "Post-Apocalyptic Precinct";
        end;
        v_u_2:get_base_fn(v12, "get_icon")
        v12.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 35 ]]
            return "rbxassetid://12940687000";
        end;
        local v_u_13 = nil
        v12.load_stage = function(_, p_u_14) --[[ Name: load_stage ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_13 ]]
            v_u_7:singleton():load_model_category(v_u_8.GameStage.PostApocalypticStage, v_u_8.Category.GameStage, function(p15) --[[ Line: 39 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_14 ]]
                v_u_13 = p15
                p_u_14()
            end)
        end;
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = v_u_5:new()
        local v_u_19 = v_u_5:new()
        local v_u_20 = nil
        local function f_update_color(p21) --[[ Name: update_color ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_20, (copy 3): v_u_19, (ref 4): v_u_17, (copy 5): v_u_18 ]]
            local v22 = v_u_6:get_server_game_instance_player_powerbar_active(p21._players._slots:get(p21:get_local_game_slot()))
            if v22 ~= v_u_20 then
                v_u_20 = v22
                local v23 = p21:get_game_note_skin_info()
                local v24 = v23:get_slot_basecolor_list(p21:get_local_game_slot())
                local v25 = v23:get_slot_fevercolor_list(p21:get_local_game_slot())
                local v26, v27, v28, v29
                if v22 then
                    v26 = v25:get(1):to_color3()
                    v27 = v25:get(2):to_color3()
                    v28 = v25:get(3):to_color3()
                    v29 = v25:get(4):to_color3()
                else
                    v26 = v24:get(1):to_color3()
                    v27 = v24:get(2):to_color3()
                    v28 = v24:get(3):to_color3()
                    v29 = v24:get(4):to_color3()
                end;
                v_u_19:clear()
                v_u_19:push_back(v26)
                v_u_19:push_back(v27)
                v_u_19:push_back(v28)
                v_u_19:push_back(v29)
                for v30, v31 in v_u_17:key_itr() do
                    v_u_18:push_back({ v31, (v_u_19:get(v30 % v_u_19:count() + 1)) })
                end;
            end;
        end;
        local function _() --[[ Name: pop_queued_color_change ]] --[[ Line: 84 ]]
            --[[ Upvalues: (copy 1): v_u_18 ]]
            if v_u_18:count() > 0 then
                local v32 = v_u_18:pop_back()
                v32[1].Color = ColorSequence.new(v32[2])
            end;
        end;
        local v_u_33 = nil
        local v_u_34 = nil
        v_u_2:get_base_fn(v12, "setup_stage")
        v12.setup_stage = function(p35, p36) --[[ Name: setup_stage ]] --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_9, (ref 3): v_u_16, (ref 4): v_u_33, (ref 5): v_u_34, (ref 6): v_u_10, (ref 7): v_u_17, (ref 8): v_u_3, (ref 9): v_u_20, (copy 10): f_update_color, (copy 11): v_u_18 ]]
            v_u_13.Parent = v_u_9:get_local_elements_folder()
            v_u_16 = v_u_13.CharacterShineProto
            local v37 = v_u_9:get_game_sky()
            v37.SkyboxBk = "rbxassetid://12424221367"
            v37.SkyboxDn = "rbxassetid://12424223298"
            v37.SkyboxFt = "rbxassetid://12424228419"
            v37.SkyboxLf = "rbxassetid://12424217291"
            v37.SkyboxRt = "rbxassetid://12424219312"
            v37.SkyboxUp = "rbxassetid://12424230154"
            local v38 = v_u_9:get_game_lighting()
            v38.Ambient = Color3.fromRGB(85, 85, 85)
            v38.Brightness = 0
            v38.ColorShift_Bottom = Color3.fromRGB(0, 0, 0)
            v38.ColorShift_Top = Color3.fromRGB(0, 0, 0)
            v38.OutdoorAmbient = Color3.fromRGB(0, 0, 0)
            v38.ClockTime = 12
            v38.GeographicLatitude = 0
            local v39 = v_u_9:get_game_atmosphere()
            v39.Density = 0
            v39.Offset = 0
            v39.Glare = 0.59
            v39.Haze = 2.02
            v39.Color = Color3.fromRGB(217, 205, 176)
            v39.Decay = Color3.fromRGB(91, 78, 14)
            v_u_9:set_game_atmosphere_enabled(true)
            v_u_33 = v_u_13.MiddleSection
            p35:on_switch_focus_slot(p36)
            v_u_34 = v_u_10:new(v_u_16, Vector3.new(0, -3.5, 0))
            v_u_17 = v_u_3:get_list_of_children_of_classname(v_u_13, "ParticleEmitter")
            v_u_17:shuffle()
            v_u_20 = nil
            f_update_color(p36)
            local v40 = 0
            while v_u_18:count() > 0 do
                if v_u_18:count() > 0 then
                    local v41 = v_u_18:pop_back()
                    v41[1].Color = ColorSequence.new(v41[2])
                end;
                v40 = v40 + 1
                if v40 > 250 then
                    break;
                end;
            end;
        end;
        v_u_2:get_base_fn(v12, "on_switch_focus_slot")
        v12.on_switch_focus_slot = function(_, p42) --[[ Name: on_switch_focus_slot ]] --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_4 ]]
            v_u_33:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p42:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v12, "teardown_stage")
        v12.teardown_stage = function(_, p43) --[[ Name: teardown_stage ]] --[[ Line: 158 ]]
            --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_16, (ref 3): v_u_17, (copy 4): v_u_18, (ref 5): v_u_13 ]]
            v_u_34:teardown(p43)
            v_u_16:Destroy()
            v_u_17:clear()
            v_u_18:clear()
            v_u_13:Destroy()
        end;
        v_u_2:get_base_fn(v12, "create_shine_for_slot_at_cframe")
        v12.create_shine_for_slot_at_cframe = function(_, p44, p45, p46) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 168 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            v_u_34:create_shine_for_slot_at_cframe(p44, p45, p46)
        end;
        v_u_2:get_base_fn(v12, "game_update")
        v12.game_update = function(_, p47, p48) --[[ Name: game_update ]] --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): v_u_34, (copy 2): f_update_color, (copy 3): v_u_18 ]]
            v_u_34:update(p47, p48)
            f_update_color(p48)
            if v_u_18:count() > 0 then
                local v49 = v_u_18:pop_back()
                v49[1].Color = ColorSequence.new(v49[2])
            end;
            if v_u_18:count() > 0 then
                local v50 = v_u_18:pop_back()
                v50[1].Color = ColorSequence.new(v50[2])
            end;
            if v_u_18:count() > 0 then
                local v51 = v_u_18:pop_back()
                v51[1].Color = ColorSequence.new(v51[2])
            end;
        end;
        v_u_2:get_base_fn(v12, "should_do_game_start_zoom_in_effect")
        v12.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 183 ]]
            return true, 49.275000000000006, 18.900000000000002, 0.75;
        end;
        return v12;
    end
};
