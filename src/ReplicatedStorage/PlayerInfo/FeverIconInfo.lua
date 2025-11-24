-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:13 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_3 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
return {
    ["get_playerblob_fevericon_owned_set"] = function(_, p7, p8, p9) --[[ Name: get_playerblob_fevericon_owned_set ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_3, (copy 4): v_u_2, (copy 5): v_u_6, (copy 6): v_u_5 ]]
        local v10 = v_u_1:new()
        v10:add_set_from_table_list(v_u_4:singleton():get_fevericon_default_available_ids_list():get_table())
        for v11, v12 in v_u_3:get_owned_crafting_materials(p7):key_itr() do
            local v13 = v_u_2:singleton():get_material(v11)
            if v12 > 0 and v13:is_fever_icon() then
                v10:add_set(v13:get_fever_icon_id())
            end;
        end;
        for v14, _ in v_u_6:playerblob_get_collection_type_database_id_set(p7, v_u_6.Type.Icons, p9):key_itr() do
            v10:add_set(v14)
        end;
        if v_u_5:playerblob_has_vip_for_current_day(p7, p8) then
            for v15, _ in v_u_5:get_vip_fevericon_ids_set():key_itr() do
                v10:add_set(v15)
            end;
        end;
        return v10;
    end
};
