-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:36 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_3 = require(game.ReplicatedStorage.Lobby.NPCNametag)
local v_u_4 = require(game.ReplicatedStorage.Lobby.NPCPopup)
local v_u_5 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v7 = require(game.ReplicatedStorage.Local.NPCList)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["NPC"] = v7,
    ["new"] = function(_, _, p_u_9) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_5, (copy 3): v_u_8, (copy 4): v_u_1, (copy 5): v_u_2, (copy 6): v_u_3, (copy 7): v_u_4 ]]
        local v13 = {
            ["update"] = function(p10, p11) --[[ Name: update ]] --[[ Line: 20 ]]
                p10:update_base(p11)
            end,
            ["get_id"] = function(_) --[[ Name: get_id ]] --[[ Line: 67 ]]
                return -1;
            end,
            ["get_root"] = function(_) --[[ Name: get_root ]] --[[ Line: 73 ]]
                return nil;
            end,
            ["setup"] = function(p12) --[[ Name: setup ]] --[[ Line: 101 ]]
                p12:setup_base()
            end,
            ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 149 ]]
                return "NPCBase";
            end,
            ["get_description"] = function(_) --[[ Name: get_description ]] --[[ Line: 150 ]]
                return "NPCBaseDescription";
            end,
            ["get_popup_proto"] = function(_) --[[ Name: get_popup_proto ]] --[[ Line: 161 ]]
                return nil;
            end,
            ["on_popup_triggered"] = function(_) end
        }
        local v_u_14 = nil
        local v_u_15 = nil
        v13.update_base = function(_, p16) --[[ Name: update_base ]] --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15 ]]
            if v_u_14 ~= nil then
                v_u_14:update(p16)
            end;
            if v_u_15 ~= nil then
                v_u_15:update(p16)
            end;
        end;
        v13.load_anim = function(_, p_u_17, p_u_18) --[[ Name: load_anim ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_5, (ref 3): v_u_8, (copy 4): p_u_9 ]]
            local v_u_19 = nil
            if v_u_6:test_enum_member(p_u_18, v_u_5) then
                v_u_8:ptry(function() --[[ Line: 32 ]]
                    --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_17, (ref 3): p_u_9, (copy 4): p_u_18 ]]
                    v_u_19 = p_u_17:LoadAnimation(p_u_9._animation_manager:get_anim(p_u_18))
                end)
            else
                local l_Animation_0 = Instance.new("Animation")
                l_Animation_0.AnimationId = p_u_18
                v_u_8:ptry(function() --[[ Line: 38 ]]
                    --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_17, (copy 3): l_Animation_0 ]]
                    v_u_19 = p_u_17:LoadAnimation(l_Animation_0)
                end)
            end;
            return v_u_19;
        end;
        local v_u_20 = nil
        v13.play_anim = function(_, p21) --[[ Name: play_anim ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            if p21 ~= v_u_20 then
                if v_u_20 ~= nil then
                    v_u_20:Stop()
                end;
                v_u_20 = p21
                if v_u_20 ~= nil then
                    v_u_20:Play()
                end;
            end;
        end;
        v13.get_current_anim_track = function(_) --[[ Name: get_current_anim_track ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        v13.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("NPC must override cleanup")
        end;
        local v_u_22 = -1
        v13.set_assigned_npc_id = function(_, p23) --[[ Name: set_assigned_npc_id ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22 = p23
        end;
        v13.get_assigned_npc_id = function(_) --[[ Name: get_assigned_npc_id ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        local v_u_24 = Vector3.new()
        local v_u_25 = true
        v13.set_needs_updated_position = function(_) --[[ Name: set_needs_updated_position ]] --[[ Line: 77 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            v_u_25 = true
        end;
        v13.get_position = function(p26) --[[ Name: get_position ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25 ]]
            if p26:get_root() == nil then
                return v_u_24;
            end;
            if v_u_25 == true then
                v_u_25 = false
                v_u_24 = p26:get_root().PrimaryPart.Position
            end;
            return v_u_24;
        end;
        v13.set_visible = function(p27, p28) --[[ Name: set_visible ]] --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_2 ]]
            if p27:get_root() == nil then
                return v_u_1:warnf("NPCBase:set_visible when root is nil");
            elseif p28 == true then
                p27:get_root().Parent = v_u_2:get_npc_root()
            else
                p27:get_root().Parent = nil
            end;
        end;
        v13.setup_base = function(p29) --[[ Name: setup_base ]] --[[ Line: 105 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            if p29:get_root() == nil then
                return v_u_1:warnf("NPCBase:setup_base when root is nil");
            end;
            p29:add_nametag()
            p29:add_popup()
        end;
        v13.add_nametag = function(p30) --[[ Name: add_nametag ]] --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_14, (ref 3): v_u_3, (copy 4): p_u_9 ]]
            if p30:get_root() == nil then
                return v_u_1:warnf("NPCBase:add_nametag when root is nil");
            end;
            v_u_14 = v_u_3:new(p_u_9, p_u_9._lobby_join:get_character_manager())
            v_u_14:create_nametag_on_character(p30:get_root(), p30:get_name(), p30:get_description())
            v_u_14:set_position_offset(p30:get_nametag_position_offset())
        end;
        v13.add_popup = function(p_u_31) --[[ Name: add_popup ]] --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_15, (ref 3): v_u_4, (copy 4): p_u_9 ]]
            if p_u_31:get_root() == nil then
                return v_u_1:warnf("NPCBase:add_popup when root is nil");
            else
                local v32 = p_u_31:get_popup_proto()
                if v32 ~= nil then
                    v_u_15 = v_u_4:new(p_u_9)
                    v_u_15:create_popup_on_character(v32, p_u_31:get_root())
                    v_u_15:set_position_offset(p_u_31:get_nametag_position_offset() + Vector3.new(0, 0.65, 0))
                    v_u_15:set_trigger_callback(function() --[[ Line: 129 ]]
                        --[[ Upvalues: (copy 1): p_u_31 ]]
                        p_u_31:on_popup_triggered()
                    end)
                end;
            end;
        end;
        v13.cleanup_nametag_and_popup = function(_) --[[ Name: cleanup_nametag_and_popup ]] --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_14, (ref 3): v_u_15 ]]
            v_u_8:ptry(function() --[[ Line: 135 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15 ]]
                if v_u_14 ~= nil then
                    v_u_14:do_remove()
                    v_u_14 = nil
                end;
                if v_u_15 ~= nil then
                    v_u_15:do_remove()
                    v_u_15 = nil
                end;
            end)
        end;
        v13.get_nametag = function(_) --[[ Name: get_nametag ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            return v_u_14;
        end;
        v13.get_popup = function(_) --[[ Name: get_popup ]] --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        local v_u_33 = Vector3.new(0, 3.5, 0)
        v13.set_nametag_position_offset = function(p34, p35) --[[ Name: set_nametag_position_offset ]] --[[ Line: 153 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_14 ]]
            v_u_33 = p35
            if v_u_14 then
                v_u_14:set_position_offset(p34:get_nametag_position_offset())
            end;
        end;
        v13.get_nametag_position_offset = function(_) --[[ Name: get_nametag_position_offset ]] --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            return v_u_33;
        end;
        return v13;
    end
};
