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
require(game.ReplicatedStorage.Shared.Dependency)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
return {
    ["get_decoration_name"] = function(_) --[[ Name: get_decoration_name ]] --[[ Line: 13 ]]
        return "LobbyTruckDance";
    end,
    ["new"] = function(_, p_u_7) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_5, (copy 6): v_u_6 ]]
        local v8 = v_u_3:new()
        v_u_1:get_base_fn(v8, "on_client_startup")
        v8.on_client_startup = function(_, p_u_9) --[[ Name: on_client_startup ]] --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_7, (ref 3): v_u_2, (ref 4): v_u_5, (ref 5): v_u_6 ]]
            v_u_4:register_webnpc_anchors_on_obj(p_u_9, p_u_7)
            local function _(p_u_10) --[[ Name: apply_song_icon_to_decal ]] --[[ Line: 22 ]]
                --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2, (ref 3): v_u_5, (ref 4): v_u_6 ]]
                p_u_9._shop_local_protocol:request_shop_info_cached(function(p_u_11) --[[ Line: 23 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_5, (ref 3): v_u_6, (copy 4): p_u_10 ]]
                    v_u_2:ptry(function() --[[ Line: 24 ]]
                        --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): p_u_10 ]]
                        local l_AvailableItems_0 = p_u_11.AvailableItems
                        local v12 = v_u_5:new()
                        for v13 = 1, #l_AvailableItems_0 do
                            local v14 = l_AvailableItems_0[v13]
                            if v14.SaleComboKey == nil then
                                v12:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v14.SongKey))
                            end;
                        end;
                        if v12:count() > 0 then
                            p_u_10.Texture = v12:random()
                        end;
                    end)
                end)
            end;
            v_u_2:ptry(function() --[[ Line: 41 ]]
                --[[ Upvalues: (ref 1): p_u_7, (copy 2): p_u_9, (ref 3): v_u_2, (ref 4): v_u_5, (ref 5): v_u_6 ]]
                local l_Decal_0 = p_u_7.ScreenSquare1.Decal
                p_u_9._shop_local_protocol:request_shop_info_cached(function(p_u_15) --[[ Line: 23 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_5, (ref 3): v_u_6, (copy 4): l_Decal_0 ]]
                    v_u_2:ptry(function() --[[ Line: 24 ]]
                        --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): l_Decal_0 ]]
                        local l_AvailableItems_1 = p_u_15.AvailableItems
                        local v16 = v_u_5:new()
                        for v17 = 1, #l_AvailableItems_1 do
                            local v18 = l_AvailableItems_1[v17]
                            if v18.SaleComboKey == nil then
                                v16:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v18.SongKey))
                            end;
                        end;
                        if v16:count() > 0 then
                            l_Decal_0.Texture = v16:random()
                        end;
                    end)
                end)
                local l_Decal_1 = p_u_7.ScreenSquare2.Decal
                p_u_9._shop_local_protocol:request_shop_info_cached(function(p_u_19) --[[ Line: 23 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_5, (ref 3): v_u_6, (copy 4): l_Decal_1 ]]
                    v_u_2:ptry(function() --[[ Line: 24 ]]
                        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): l_Decal_1 ]]
                        local l_AvailableItems_2 = p_u_19.AvailableItems
                        local v20 = v_u_5:new()
                        for v21 = 1, #l_AvailableItems_2 do
                            local v22 = l_AvailableItems_2[v21]
                            if v22.SaleComboKey == nil then
                                v20:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v22.SongKey))
                            end;
                        end;
                        if v20:count() > 0 then
                            l_Decal_1.Texture = v20:random()
                        end;
                    end)
                end)
                local l_Decal_2 = p_u_7.ScreenSquare3.Decal
                p_u_9._shop_local_protocol:request_shop_info_cached(function(p_u_23) --[[ Line: 23 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_5, (ref 3): v_u_6, (copy 4): l_Decal_2 ]]
                    v_u_2:ptry(function() --[[ Line: 24 ]]
                        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): l_Decal_2 ]]
                        local l_AvailableItems_3 = p_u_23.AvailableItems
                        local v24 = v_u_5:new()
                        for v25 = 1, #l_AvailableItems_3 do
                            local v26 = l_AvailableItems_3[v25]
                            if v26.SaleComboKey == nil then
                                v24:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v26.SongKey))
                            end;
                        end;
                        if v24:count() > 0 then
                            l_Decal_2.Texture = v24:random()
                        end;
                    end)
                end)
                local l_Decal_3 = p_u_7.ScreenSquare4.Decal
                p_u_9._shop_local_protocol:request_shop_info_cached(function(p_u_27) --[[ Line: 23 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_5, (ref 3): v_u_6, (copy 4): l_Decal_3 ]]
                    v_u_2:ptry(function() --[[ Line: 24 ]]
                        --[[ Upvalues: (copy 1): p_u_27, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): l_Decal_3 ]]
                        local l_AvailableItems_4 = p_u_27.AvailableItems
                        local v28 = v_u_5:new()
                        for v29 = 1, #l_AvailableItems_4 do
                            local v30 = l_AvailableItems_4[v29]
                            if v30.SaleComboKey == nil then
                                v28:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v30.SongKey))
                            end;
                        end;
                        if v28:count() > 0 then
                            l_Decal_3.Texture = v28:random()
                        end;
                    end)
                end)
            end)
        end;
        return v8;
    end
};
