-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:10 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = {
    ["get_max_songs"] = function(_) --[[ Name: get_max_songs ]] --[[ Line: 55 ]]
        return 500;
    end
}
v_u_2.new = function(_, p_u_3) --[[ Name: new ]] --[[ Line: 5 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v4 = {}
    local v_u_5 = v_u_1:new()
    v4.get_rbxid = function(_) --[[ Name: get_rbxid ]] --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): p_u_3 ]]
        return p_u_3;
    end;
    v4.get_songs_list = function(_) --[[ Name: get_songs_list ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        return v_u_5;
    end;
    v4.set_songs_list = function(_, p6) --[[ Name: set_songs_list ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        v_u_5:clear()
        v_u_5:push_back_table_list(p6)
    end;
    v4.add_song = function(_, p7) --[[ Name: add_song ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_2 ]]
        if v_u_5:contains(p7) == false and v_u_5:count() < v_u_2:get_max_songs() then
            v_u_5:push_back(p7)
        end;
    end;
    v4.remove_song = function(_, p8) --[[ Name: remove_song ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        v_u_5:remove(p8)
    end;
    v4.is_song_in_list = function(_, p9) --[[ Name: is_song_in_list ]] --[[ Line: 28 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        return v_u_5:contains(p9);
    end;
    v4.count = function(_) --[[ Name: count ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        return v_u_5:count();
    end;
    v4.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): p_u_3 ]]
        return {
            ["RbxId"] = p_u_3,
            ["SongsList"] = v_u_5._table
        };
    end;
    return v4;
end;
v_u_2.from_table = function(_, p10) --[[ Name: from_table ]] --[[ Line: 49 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    local v11 = v_u_2:new(p10.RbxId)
    v11:set_songs_list(p10.SongsList)
    return v11;
end;
return v_u_2;
