-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:06 PM
-- Time elapsed: 12 milliseconds

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 18 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_10 ]]
    v_u_7 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
    v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_9 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_10 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (ref 5): v_u_8, (ref 6): v_u_9, (copy 7): v_u_3, (copy 8): v_u_4 ]]
        local v11 = v_u_1:new()
        v_u_2:get_base_fn(v11, "get_name")
        v11.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 31 ]]
            return "Halloween Haunts";
        end;
        v_u_2:get_base_fn(v11, "get_icon")
        v11.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 33 ]]
            return "rbxassetid://10678194037";
        end;
        local v_u_12 = nil
        v11.load_stage = function(_, p_u_13) --[[ Name: load_stage ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_12 ]]
            v_u_5:singleton():load_model_category(v_u_6.GameStage.HalloweenStage, v_u_6.Category.GameStage, function(p14) --[[ Line: 37 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_13 ]]
                v_u_12 = p14
                p_u_13()
            end)
        end;
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        v_u_2:get_base_fn(v11, "setup_stage")
        v11.setup_stage = function(p19, p20) --[[ Name: setup_stage ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_12, (ref 3): v_u_16, (ref 4): v_u_8, (ref 5): v_u_17, (ref 6): v_u_9, (ref 7): v_u_18, (ref 8): v_u_3 ]]
            v_u_15 = v_u_12.CharacterShineProto1
            v_u_15.Parent = nil
            v_u_16 = v_u_12.CharacterShineProto2
            v_u_16.Parent = nil
            v_u_8:get_game_lighting().ClockTime = 0
            v_u_12.Parent = v_u_8:get_local_elements_folder()
            v_u_17 = v_u_9:new(v_u_15, Vector3.new(0, -3.5, 0))
            v_u_17:add_shine_proto(v_u_16)
            v_u_18 = v_u_12.FaceToPlayer
            p19:on_switch_focus_slot(p20)
            local v21 = v_u_8:get_game_sky()
            v21.SkyboxBk = "rbxassetid://10677598416"
            v21.SkyboxDn = "rbxassetid://10677576051"
            v21.SkyboxFt = "rbxassetid://10677598416"
            v21.SkyboxLf = "rbxassetid://10677598416"
            v21.SkyboxRt = "rbxassetid://10677598416"
            v21.SkyboxUp = "rbxassetid://10677575916"
            local v22 = v_u_8:get_game_lighting()
            v22.Ambient = v_u_3:new(85, 85, 85):to_color3()
            v22.Brightness = 0
            v22.ColorShift_Bottom = v_u_3:new(0, 0, 0):to_color3()
            v22.ColorShift_Top = v_u_3:new(0, 0, 0):to_color3()
            v22.OutdoorAmbient = v_u_3:new(0, 0, 0):to_color3()
            v22.ClockTime = 10.8
            v22.GeographicLatitude = 118
        end;
        local function _(p23, p24) --[[ Name: update_shine_cframe ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            p24:set_cframe(CFrame.new(p24:get_cframe().p, v_u_4:slot_to_world_position(p23:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v11, "on_switch_focus_slot")
        v11.on_switch_focus_slot = function(_, p25) --[[ Name: on_switch_focus_slot ]] --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_18, (ref 3): v_u_17 ]]
            v_u_18:SetPrimaryPartCFrame((CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p25:get_local_game_slot()))))
            for _, v26 in v_u_17:get_character_shines_list():key_itr() do
                v26:set_cframe(CFrame.new(v26:get_cframe().p, v_u_4:slot_to_world_position(p25:get_local_game_slot())))
            end;
        end;
        v_u_2:get_base_fn(v11, "create_shine_for_slot_at_cframe")
        v11.create_shine_for_slot_at_cframe = function(_, p27, p28, p29) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_4 ]]
            local v30 = v_u_17:create_shine_for_slot_at_cframe(p27, p28, p29)
            v30:set_cframe(CFrame.new(v30:get_cframe().p, v_u_4:slot_to_world_position(p27:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v11, "game_update")
        v11.game_update = function(_, p31, p32) --[[ Name: game_update ]] --[[ Line: 110 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:update(p31, p32)
        end;
        v_u_2:get_base_fn(v11, "teardown_stage")
        v11.teardown_stage = function(_, p33) --[[ Name: teardown_stage ]] --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_12, (ref 3): v_u_15, (ref 4): v_u_16 ]]
            v_u_17:teardown(p33)
            v_u_12:Destroy()
            v_u_15:Destroy()
            v_u_16:Destroy()
        end;
        v_u_2:get_base_fn(v11, "should_do_game_start_zoom_in_effect")
        v11.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 123 ]]
            return true, 49.275000000000006, 18.900000000000002, 0.75;
        end;
        return v11;
    end
};
