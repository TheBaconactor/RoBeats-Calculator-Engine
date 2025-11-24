-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.Override)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.WebNPCAnchors)
local v_u_3 = require(game.ReplicatedStorage.LobbyDecoration.DecorationClasses.LobbyDecorationBase)
local v_u_4 = require(game.ReplicatedStorage.LobbyDecoration.LobbyDecorationUtil)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_7 = nil
v5:require_client(function() --[[ Line: 11 ]]
    --[[ Upvalues: (ref 1): v_u_7 ]]
    v_u_7 = require(game.ReplicatedStorage.Lobby.Menus.NewsUI)
end)
return {
    ["get_decoration_name"] = function(_) --[[ Name: get_decoration_name ]] --[[ Line: 17 ]]
        return "LobbyTruckNews";
    end,
    ["new"] = function(_, p_u_8) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_2, (ref 5): v_u_7, (copy 6): v_u_6 ]]
        local v9 = v_u_3:new()
        v_u_1:get_base_fn(v9, "on_client_startup")
        v9.on_client_startup = function(_, p_u_10) --[[ Name: on_client_startup ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_8, (ref 3): v_u_2, (ref 4): v_u_7, (ref 5): v_u_6 ]]
            v_u_4:register_webnpc_anchors_on_obj(p_u_10, p_u_8)
            local v11 = p_u_8:FindFirstChild("DisplayScreen")
            if v11 then
                local v_u_12 = v_u_2:get_list_of_children_of_classname(v11, "Decal")
                v_u_7:get_cached_news_data(function(p13) --[[ Line: 28 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_2, (copy 3): v_u_12, (copy 4): p_u_10 ]]
                    local v_u_14 = v_u_6:new()
                    for v15 = 1, #p13 do
                        local l_ImageAssetId_0 = p13[v15].ImageAssetId
                        if l_ImageAssetId_0 ~= nil and #l_ImageAssetId_0 > 0 then
                            v_u_14:push_back(l_ImageAssetId_0)
                        end;
                    end;
                    local function _() --[[ Name: update_news_display_images ]] --[[ Line: 38 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_14, (ref 3): v_u_12 ]]
                        local v16 = v_u_2:placeholder_assetid()
                        if v_u_14:count() > 0 then
                            v16 = v_u_14:random()
                        end;
                        for _, v17 in v_u_12:key_itr() do
                            v17.Texture = v16
                        end;
                    end;
                    local v18 = v_u_2:placeholder_assetid()
                    if v_u_14:count() > 0 then
                        v18 = v_u_14:random()
                    end;
                    for _, v19 in v_u_12:key_itr() do
                        v19.Texture = v18
                    end;
                    p_u_10._lobby_join:register_lobby_join_start_fn(function(_) --[[ Line: 49 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_14, (ref 3): v_u_12 ]]
                        local v20 = v_u_2:placeholder_assetid()
                        if v_u_14:count() > 0 then
                            v20 = v_u_14:random()
                        end;
                        for _, v21 in v_u_12:key_itr() do
                            v21.Texture = v20
                        end;
                    end)
                end)
            end;
        end;
        return v9;
    end
};
