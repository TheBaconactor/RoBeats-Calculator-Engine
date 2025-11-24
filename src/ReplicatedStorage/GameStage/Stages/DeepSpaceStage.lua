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
require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_8 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_9 = nil
local v_u_10 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10 ]]
    v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_10 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_8, (ref 5): v_u_9, (ref 6): v_u_10, (copy 7): v_u_6, (copy 8): v_u_5, (copy 9): v_u_3, (copy 10): v_u_4 ]]
        local v11 = v_u_1:new()
        v_u_2:get_base_fn(v11, "get_name")
        v11.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 31 ]]
            return "Hyperspace (SDVB)";
        end;
        v_u_2:get_base_fn(v11, "get_icon")
        v11.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 33 ]]
            return "rbxassetid://9583129650";
        end;
        local v_u_12 = nil
        v11.load_stage = function(_, p_u_13) --[[ Name: load_stage ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_12 ]]
            v_u_7:singleton():load_model_category(v_u_8.GameStage.DeepSpaceStage, v_u_8.Category.GameStage, function(p14) --[[ Line: 38 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_13 ]]
                v_u_12 = p14
                p_u_13()
            end)
        end;
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = 0
        local v_u_22 = nil
        v_u_2:get_base_fn(v11, "setup_stage")
        v11.setup_stage = function(p23, p24) --[[ Name: setup_stage ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_12, (ref 3): v_u_15, (ref 4): v_u_9, (ref 5): v_u_22, (ref 6): v_u_10, (ref 7): v_u_17, (ref 8): v_u_18, (ref 9): v_u_19, (ref 10): v_u_20, (ref 11): v_u_6, (ref 12): v_u_5, (ref 13): v_u_3 ]]
            v_u_16 = v_u_12.CharacterShineProto
            v_u_16.Parent = nil
            v_u_15 = v_u_12.Stage
            local v25
            if p24:show_fullscreen_mobile_ui() then
                v_u_12.Stage.TextureMotionPC.Parent = nil
                v25 = v_u_12.Stage.TextureMotionMobile
            else
                v25 = v_u_12.Stage.TextureMotionPC
                v_u_12.Stage.TextureMotionMobile.Parent = nil
            end;
            v_u_12.Parent = v_u_9:get_local_elements_folder()
            v_u_22 = v_u_10:new(v_u_16, Vector3.new(0, -3.5, 0))
            p23:on_switch_focus_slot(p24)
            local v26 = v_u_9:get_game_sky()
            v26.SkyboxBk = "http://www.roblox.com/asset/?id=159454299"
            v26.SkyboxDn = "http://www.roblox.com/asset/?id=159454296"
            v26.SkyboxFt = "http://www.roblox.com/asset/?id=159454293"
            v26.SkyboxLf = "http://www.roblox.com/asset/?id=159454286"
            v26.SkyboxRt = "http://www.roblox.com/asset/?id=159454300"
            v26.SkyboxUp = "http://www.roblox.com/asset/?id=159454288"
            v_u_17 = v_u_15.CenterEmitter.BillboardGui.Frame.Glow1
            v_u_18 = v_u_15.CenterEmitter.BillboardGui.Frame.Glow2
            v_u_19 = v_u_15.CenterEmitter.BillboardGui.Frame.Glow3
            v_u_20 = v_u_15.CenterEmitter.BillboardGui.Frame.Glow4
            local v27 = v_u_5:YForPointOf2PtLineP1P2X(5, 0.5, 30, 2, v_u_3:clamp(v_u_6:singleton():get_difficulty_for_key(p24:es_gamelocal_get_audiomanager():get_song_key()), 5, 30))
            v25.TextureMotion1.LeftBeamNormal.TextureSpeed = v27
            v25.TextureMotion1.LeftBeamClear.TextureSpeed = -v27
            v25.TextureMotion1.RightBeamNormal.TextureSpeed = v27
            v25.TextureMotion1.RightBeamClear.TextureSpeed = -v27
            v25.TextureMotion2.LeftBeamNormal.TextureSpeed = v27
            v25.TextureMotion2.LeftBeamClear.TextureSpeed = -v27
            v25.TextureMotion2.RightBeamNormal.TextureSpeed = v27
            v25.TextureMotion2.RightBeamClear.TextureSpeed = -v27
        end;
        v_u_2:get_base_fn(v11, "on_switch_focus_slot")
        v11.on_switch_focus_slot = function(_, p28) --[[ Name: on_switch_focus_slot ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_4 ]]
            v_u_15:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p28:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v11, "create_shine_for_slot_at_cframe")
        v11.create_shine_for_slot_at_cframe = function(_, p29, p30, p31) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22:create_shine_for_slot_at_cframe(p29, p30, p31)
        end;
        v_u_2:get_base_fn(v11, "teardown_stage")
        v11.teardown_stage = function(_, p32) --[[ Name: teardown_stage ]] --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_12, (ref 3): v_u_15, (ref 4): v_u_16 ]]
            v_u_22:teardown(p32)
            v_u_12:Destroy()
            v_u_15:Destroy()
            v_u_16:Destroy()
        end;
        v_u_2:get_base_fn(v11, "game_update")
        v11.game_update = function(_, p33, p34) --[[ Name: game_update ]] --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_21, (ref 3): v_u_5, (ref 4): v_u_17, (ref 5): v_u_3, (ref 6): v_u_18, (ref 7): v_u_19, (ref 8): v_u_20 ]]
            v_u_22:update(p33, p34)
            v_u_21 = v_u_5:IncrementWrap(v_u_21, v_u_5:SecondsToTick(1.75) * p33, 1)
            local v35 = v_u_5:YForPointOf2PtLineP1P2X(-1, 0.75, 1, 1, (math.sin(v_u_21 * 2 * 3.141592653589793)))
            v_u_17.ImageTransparency = v_u_3:tra(v35)
            v_u_18.ImageTransparency = v_u_3:tra(v35 * 0.5)
            v_u_19.ImageTransparency = v_u_3:tra(v35 * 0.25)
            v_u_20.ImageTransparency = v_u_3:tra(v35 * 0.25)
        end;
        return v11;
    end
};
