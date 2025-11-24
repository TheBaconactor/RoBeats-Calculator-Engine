-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:37 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Lobby.NPC.NPCBase)
local v_u_2 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_3 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.NoCollideGroup)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPDict):new(require(game.ReplicatedStorage.CodeGen.ModelLoadDBNPCCFrames))
return {
    ["new"] = function(_, p_u_8, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_3, (copy 6): v_u_7, (copy 7): v_u_5 ]]
        local v_u_17 = v_u_1:new(p_u_8, p_u_9)
        local v_u_18 = nil
        local v_u_19 = v_u_6:new()
        local function _() --[[ Name: cons ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_10, (ref 3): v_u_2, (copy 4): p_u_14, (copy 5): p_u_9, (copy 6): p_u_8, (ref 7): v_u_3, (copy 8): p_u_11, (ref 9): v_u_7, (ref 10): v_u_5, (ref 11): v_u_18, (copy 12): p_u_15, (copy 13): v_u_17, (copy 14): v_u_19 ]]
            local v_u_20 = v_u_4:get_id_to_name():get(p_u_10)
            v_u_2:load_db_npc_character_and_humanoid(v_u_20, p_u_14, function(p21, p22) --[[ Line: 20 ]]
                --[[ Upvalues: (ref 1): p_u_9, (ref 2): p_u_8, (ref 3): v_u_3, (ref 4): p_u_11, (ref 5): v_u_7, (copy 6): v_u_20, (ref 7): v_u_5, (ref 8): v_u_18, (ref 9): p_u_15, (ref 10): v_u_17, (ref 11): v_u_19 ]]
                if p_u_9._lobby_join:get_lobby() ~= p_u_8 then
                    p21:Destroy()
                    return v_u_3:warnf("NPCAsyncLoad(%s) loaded after lobby destroyed", p_u_11);
                end;
                if p21.PrimaryPart then
                    if v_u_7:contains(v_u_20) then
                        p21:SetPrimaryPartCFrame(v_u_7:get(v_u_20))
                    else
                        v_u_3:warnf("CodeGen.ModelLoadDBNPCCFrames does not contain(%s). Run command \'%s\'.", v_u_20, "require(game.ServerStorage.CodeGenRunner.Run)()")
                    end;
                end;
                p21.Name = p_u_11
                v_u_5:apply_group_id(p21, p_u_8:get_character_group_id())
                v_u_18 = p21
                if p_u_15 then
                    p_u_15(v_u_17, p21, p22)
                end;
                v_u_17:setup_base()
                v_u_17:set_needs_updated_position()
                p_u_8._npcs:flag_update_npcs()
                for _, v23 in v_u_19:key_itr() do
                    v23(v_u_18)
                end;
                v_u_19:clear()
            end)
        end;
        v_u_17.get_on_loaded_fns = function(_) --[[ Name: get_on_loaded_fns ]] --[[ Line: 53 ]]
            --[[ Upvalues: (copy 1): v_u_19 ]]
            return v_u_19;
        end;
        v_u_17.add_on_loaded_fn = function(_, p24) --[[ Name: add_on_loaded_fn ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_19 ]]
            if v_u_18 == nil then
                v_u_19:push_back(p24)
            else
                p24(v_u_18)
            end;
        end;
        v_u_17.setup = function(_) end;
        local v_u_25 = nil
        v_u_17.add_update_fn = function(_, p26) --[[ Name: add_update_fn ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_6 ]]
            if v_u_25 == nil then
                v_u_25 = v_u_6:new()
            end;
            v_u_25:push_back(p26)
        end;
        v_u_17.update = function(p27, p28) --[[ Name: update ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            p27:update_base(p28)
            if v_u_25 then
                for _, v29 in v_u_25:key_itr() do
                    v29(p28)
                end;
            end;
        end;
        v_u_17.cleanup = function(p30) --[[ Name: cleanup ]] --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_25 ]]
            p30:cleanup_nametag_and_popup()
            if v_u_18 then
                v_u_18:Destroy()
                v_u_18 = nil
            end;
            if v_u_25 then
                v_u_25:clear()
            end;
        end;
        v_u_17.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 91 ]]
            --[[ Upvalues: (copy 1): p_u_10 ]]
            return p_u_10;
        end;
        v_u_17.get_root = function(_) --[[ Name: get_root ]] --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        v_u_17.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 96 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            return p_u_11;
        end;
        v_u_17.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 97 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            return p_u_12;
        end;
        v_u_17.get_popup_proto = function(_) --[[ Name: get_popup_proto ]] --[[ Line: 99 ]]
            --[[ Upvalues: (copy 1): p_u_13 ]]
            return p_u_13;
        end;
        v_u_17.on_popup_triggered = function(_) --[[ Name: on_popup_triggered ]] --[[ Line: 100 ]]
            --[[ Upvalues: (copy 1): p_u_9, (copy 2): p_u_16, (copy 3): p_u_8 ]]
            local l__menus_0 = p_u_9._menus
            local l__spui_0 = p_u_9._spui
            if p_u_16 then
                p_u_16(p_u_8, l__spui_0, l__menus_0)
            end;
        end;
        local v_u_31 = v_u_4:get_id_to_name():get(p_u_10)
        v_u_2:load_db_npc_character_and_humanoid(v_u_31, p_u_14, function(p32, p33) --[[ Line: 20 ]]
            --[[ Upvalues: (copy 1): p_u_9, (copy 2): p_u_8, (ref 3): v_u_3, (copy 4): p_u_11, (ref 5): v_u_7, (copy 6): v_u_31, (ref 7): v_u_5, (ref 8): v_u_18, (copy 9): p_u_15, (copy 10): v_u_17, (copy 11): v_u_19 ]]
            if p_u_9._lobby_join:get_lobby() ~= p_u_8 then
                p32:Destroy()
                return v_u_3:warnf("NPCAsyncLoad(%s) loaded after lobby destroyed", p_u_11);
            end;
            if p32.PrimaryPart then
                if v_u_7:contains(v_u_31) then
                    p32:SetPrimaryPartCFrame(v_u_7:get(v_u_31))
                else
                    v_u_3:warnf("CodeGen.ModelLoadDBNPCCFrames does not contain(%s). Run command \'%s\'.", v_u_31, "require(game.ServerStorage.CodeGenRunner.Run)()")
                end;
            end;
            p32.Name = p_u_11
            v_u_5:apply_group_id(p32, p_u_8:get_character_group_id())
            v_u_18 = p32
            if p_u_15 then
                p_u_15(v_u_17, p32, p33)
            end;
            v_u_17:setup_base()
            v_u_17:set_needs_updated_position()
            p_u_8._npcs:flag_update_npcs()
            for _, v34 in v_u_19:key_itr() do
                v34(v_u_18)
            end;
            v_u_19:clear()
        end)
        return v_u_17;
    end
};
