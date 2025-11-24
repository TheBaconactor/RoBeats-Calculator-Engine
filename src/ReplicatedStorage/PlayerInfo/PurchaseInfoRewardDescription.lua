-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:13 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v5 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v6 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v7 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
local v8 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v9 = v1:new()
local v10 = {
    [l_ProductID_Star1_V3_0] = v11:push_back_table_list(v12),
    [l_ProductID_Star2_V3_0] = v13:push_back_table_list(v14),
    [l_ProductID_Star3_V3_0] = v15:push_back_table_list(v16),
    [l_ProductID_Star4_V3_0] = v17:push_back_table_list(v18),
    [l_ProductID_Coin1_V3_0] = v19:push_back_table_list(v20),
    [l_ProductID_Coin2_V3_0] = v21:push_back_table_list(v22),
    [l_ProductID_Coin3_V3_0] = v23:push_back_table_list(v24),
    [l_ProductID_Coin4_V3_0] = v25:push_back_table_list(v26),
    [l_ProductID_StarterPack_V3_0] = v27:push_back_table_list(v28),
    [l_ProductID_CoinPack_V3_0] = v29:push_back_table_list(v30),
    [l_ProductID_StarPack_V3_0] = v31:push_back_table_list(v32),
    [l_ProductID_VIP_1Month_0] = v33:push_back_table_list(v34),
    [l_ProductID_VIP_3Month_0] = v35:push_back_table_list(v36),
    [l_ProductID_VIP_6Month_0] = v37:push_back_table_list(v38),
    [l_ProductID_ChallengePassSeasonUnlock_0] = v39:push_back_table_list(v40),
    [l_ProductID_ChallengePassComplete_0] = v41:push_back_table_list(v42),
    [l_ProductID_EventPoint1000_0] = v43:push_back_table_list(v44),
    [l_ProductID_EventPoint2000_0] = v45:push_back_table_list(v46),
    [l_ProductID_ChallengePassV2UnlockVIPTier_0] = v47:push_back_table_list(v48),
    [l_ProductID_ChallengePassV2Points250_0] = v49:push_back_table_list(v50),
    [l_ProductID_ChallengePassV2Points500_0] = v51:push_back_table_list(v52),
    [l_ProductID_ChallengePassV2Points1000_0] = v53:push_back_table_list(v54),
    [l_ProductID_UpgradeBoost_5_0] = v55:push_back_table_list(v56),
    [l_ProductID_UpgradeBoost_20_0] = v57:push_back_table_list(v58),
    [l_ProductID_UpgradeBoost_50_0] = v59:push_back_table_list(v60),
    [l_ProductID_UpgradeBoost_100_0] = v61:push_back_table_list(v62),
    [l_ProductID_UpgradeProtect_5_0] = v63:push_back_table_list(v64),
    [l_ProductID_UpgradeProtect_20_0] = v65:push_back_table_list(v66),
    [l_ProductID_UpgradeProtect_50_0] = v67:push_back_table_list(v68),
    [l_ProductID_UpgradeProtect_100_0] = v69:push_back_table_list(v70),
    [l_ProductID_GemBox_10_0] = v71:push_back_table_list(v72),
    [l_ProductID_GemBox_30_0] = v73:push_back_table_list(v74),
    [l_ProductID_GemBox_100_0] = v75:push_back_table_list(v76),
    [l_ProductID_GemBox_225_0] = v77:push_back_table_list(v78),
    [l_ProductID_TokenBox_1_0] = v79:push_back_table_list(v80),
    [l_ProductID_TokenBox_5_0] = v81:push_back_table_list(v82),
    [l_ProductID_TokenBox_10_0] = v83:push_back_table_list(v84),
    [l_ProductID_TokenBox_20_0] = v85:push_back_table_list(v86),
    [l_ProductID_Mini1StarBox_5_0] = v87:push_back_table_list(v88),
    [l_ProductID_Mini1StarBox_15_0] = v89:push_back_table_list(v90),
    [l_ProductID_Mini1StarBox_40_0] = v91:push_back_table_list(v92),
    [l_ProductID_Mini1StarBox_80_0] = v93:push_back_table_list(v94),
    [l_ProductID_Mini2StarBox_1_0] = v95:push_back_table_list(v96),
    [l_ProductID_Mini2StarBox_5_0] = v97:push_back_table_list(v98),
    [l_ProductID_Mini2StarBox_15_0] = v99:push_back_table_list(v100),
    [l_ProductID_Mini2StarBox_35_0] = v101:push_back_table_list(v102)
}
local l_ProductID_Star1_V3_0 = v6.ProductID_Star1_V3
local v11 = v_u_2:new()
local v12 = { v5.RewardInfo:new(v5.RewardType.Stars, 15, -1) }
local l_ProductID_Star2_V3_0 = v6.ProductID_Star2_V3
local v13 = v_u_2:new()
local v14 = { v5.RewardInfo:new(v5.RewardType.Stars, 35, -1) }
local l_ProductID_Star3_V3_0 = v6.ProductID_Star3_V3
local v15 = v_u_2:new()
local v16 = { v5.RewardInfo:new(v5.RewardType.Stars, 200, -1) }
local l_ProductID_Star4_V3_0 = v6.ProductID_Star4_V3
local v17 = v_u_2:new()
local v18 = { v5.RewardInfo:new(v5.RewardType.Stars, 425, -1) }
local l_ProductID_Coin1_V3_0 = v6.ProductID_Coin1_V3
local v19 = v_u_2:new()
local v20 = { v5.RewardInfo:new(v5.RewardType.Coins, 1000, -1) }
local l_ProductID_Coin2_V3_0 = v6.ProductID_Coin2_V3
local v21 = v_u_2:new()
local v22 = { v5.RewardInfo:new(v5.RewardType.Coins, 2250, -1) }
local l_ProductID_Coin3_V3_0 = v6.ProductID_Coin3_V3
local v23 = v_u_2:new()
local v24 = { v5.RewardInfo:new(v5.RewardType.Coins, 12000, -1) }
local l_ProductID_Coin4_V3_0 = v6.ProductID_Coin4_V3
local v25 = v_u_2:new()
local v26 = { v5.RewardInfo:new(v5.RewardType.Coins, 25000, -1) }
local l_ProductID_StarterPack_V3_0 = v6.ProductID_StarterPack_V3
local v27 = v_u_2:new()
local v28 = {
    v5.RewardInfo:new(v5.RewardType.Coins, 5000, -1),
    v5.RewardInfo:new(v5.RewardType.Stars, 25, -1),
    v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 15, v7:get_small_note_box_id()),
    v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 10, v7:get_medium_note_box_id()),
    v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v7:get_large_note_box_id()),
    v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v7:get_vip_song_normal_box_id()),
    v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v7:get_vip_song_hard_box_id())
}
local l_ProductID_CoinPack_V3_0 = v6.ProductID_CoinPack_V3
local v29 = v_u_2:new()
local v30 = { v5.RewardInfo:new(v5.RewardType.Coins, 5000, -1), v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v7:get_gem_box_id()), v5.RewardInfo:new(v5.RewardType.RandomToken, 5, -1) }
local l_ProductID_StarPack_V3_0 = v6.ProductID_StarPack_V3
local v31 = v_u_2:new()
local v32 = { v5.RewardInfo:new(v5.RewardType.Stars, 25, -1), v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v7:get_gem_box_id()), v5.RewardInfo:new(v5.RewardType.RandomToken, 5, -1) }
local l_ProductID_VIP_1Month_0 = v6.ProductID_VIP_1Month
local v33 = v_u_2:new()
local v34 = { v5.RewardInfo:new(v5.RewardType.VIP, 30, -1) }
local l_ProductID_VIP_3Month_0 = v6.ProductID_VIP_3Month
local v35 = v_u_2:new()
local v36 = { v5.RewardInfo:new(v5.RewardType.VIP, 90, -1) }
local l_ProductID_VIP_6Month_0 = v6.ProductID_VIP_6Month
local v37 = v_u_2:new()
local v38 = { v5.RewardInfo:new(v5.RewardType.VIP, 180, -1) }
local l_ProductID_ChallengePassSeasonUnlock_0 = v6.ProductID_ChallengePassSeasonUnlock
local v39 = v_u_2:new()
local v40 = { v5.RewardInfo:new(v5.RewardType.ChallengePassSeasonUnlock, 1, -1) }
local l_ProductID_ChallengePassComplete_0 = v6.ProductID_ChallengePassComplete
local v41 = v_u_2:new()
local v42 = { v5.RewardInfo:new(v5.RewardType.ChallengePassComplete, 1, -1) }
local l_ProductID_EventPoint1000_0 = v6.ProductID_EventPoint1000
local v43 = v_u_2:new()
local v44 = { v5.RewardInfo:new(v5.RewardType.EventPointPurchaseRewards, 1, -1), v5.RewardInfo:new(v5.RewardType.EventPoints, 1000, -1) }
local l_ProductID_EventPoint2000_0 = v6.ProductID_EventPoint2000
local v45 = v_u_2:new()
local v46 = { v5.RewardInfo:new(v5.RewardType.EventPointPurchaseRewards, 2, -1), v5.RewardInfo:new(v5.RewardType.EventPoints, 2000, -1) }
local l_ProductID_ChallengePassV2UnlockVIPTier_0 = v6.ProductID_ChallengePassV2UnlockVIPTier
local v47 = v_u_2:new()
local v48 = { v5.RewardInfo:new(v5.RewardType.ChallengePassV2VIPTierUnlock, 1, -1) }
local l_ProductID_ChallengePassV2Points250_0 = v6.ProductID_ChallengePassV2Points250
local v49 = v_u_2:new()
local v50 = { v5.RewardInfo:new(v5.RewardType.ChallengePassV2Points, 250, -1) }
local l_ProductID_ChallengePassV2Points500_0 = v6.ProductID_ChallengePassV2Points500
local v51 = v_u_2:new()
local v52 = { v5.RewardInfo:new(v5.RewardType.ChallengePassV2Points, 500, -1) }
local l_ProductID_ChallengePassV2Points1000_0 = v6.ProductID_ChallengePassV2Points1000
local v53 = v_u_2:new()
local v54 = { v5.RewardInfo:new(v5.RewardType.ChallengePassV2Points, 1000, -1) }
local l_ProductID_UpgradeBoost_5_0 = v6.ProductID_UpgradeBoost_5
local v55 = v_u_2:new()
local v56 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v8:singleton():get_upgrade_boost_material_id()) }
local l_ProductID_UpgradeBoost_20_0 = v6.ProductID_UpgradeBoost_20
local v57 = v_u_2:new()
local v58 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 20, v8:singleton():get_upgrade_boost_material_id()) }
local l_ProductID_UpgradeBoost_50_0 = v6.ProductID_UpgradeBoost_50
local v59 = v_u_2:new()
local v60 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 50, v8:singleton():get_upgrade_boost_material_id()) }
local l_ProductID_UpgradeBoost_100_0 = v6.ProductID_UpgradeBoost_100
local v61 = v_u_2:new()
local v62 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 100, v8:singleton():get_upgrade_boost_material_id()) }
local l_ProductID_UpgradeProtect_5_0 = v6.ProductID_UpgradeProtect_5
local v63 = v_u_2:new()
local v64 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v8:singleton():get_upgrade_protect_material_id()) }
local l_ProductID_UpgradeProtect_20_0 = v6.ProductID_UpgradeProtect_20
local v65 = v_u_2:new()
local v66 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 20, v8:singleton():get_upgrade_protect_material_id()) }
local l_ProductID_UpgradeProtect_50_0 = v6.ProductID_UpgradeProtect_50
local v67 = v_u_2:new()
local v68 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 50, v8:singleton():get_upgrade_protect_material_id()) }
local l_ProductID_UpgradeProtect_100_0 = v6.ProductID_UpgradeProtect_100
local v69 = v_u_2:new()
local v70 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 100, v8:singleton():get_upgrade_protect_material_id()) }
local l_ProductID_GemBox_10_0 = v6.ProductID_GemBox_10
local v71 = v_u_2:new()
local v72 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 10, v7:get_gem_box_id()) }
local l_ProductID_GemBox_30_0 = v6.ProductID_GemBox_30
local v73 = v_u_2:new()
local v74 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 30, v7:get_gem_box_id()) }
local l_ProductID_GemBox_100_0 = v6.ProductID_GemBox_100
local v75 = v_u_2:new()
local v76 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 100, v7:get_gem_box_id()) }
local l_ProductID_GemBox_225_0 = v6.ProductID_GemBox_225
local v77 = v_u_2:new()
local v78 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 225, v7:get_gem_box_id()) }
local l_ProductID_TokenBox_1_0 = v6.ProductID_TokenBox_1
local v79 = v_u_2:new()
local v80 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 1, v7:get_token_box_id()) }
local l_ProductID_TokenBox_5_0 = v6.ProductID_TokenBox_5
local v81 = v_u_2:new()
local v82 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v7:get_token_box_id()) }
local l_ProductID_TokenBox_10_0 = v6.ProductID_TokenBox_10
local v83 = v_u_2:new()
local v84 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 10, v7:get_token_box_id()) }
local l_ProductID_TokenBox_20_0 = v6.ProductID_TokenBox_20
local v85 = v_u_2:new()
local v86 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 20, v7:get_token_box_id()) }
local l_ProductID_Mini1StarBox_5_0 = v6.ProductID_Mini1StarBox_5
local v87 = v_u_2:new()
local v88 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v7:get_mini_1star_box_id()) }
local l_ProductID_Mini1StarBox_15_0 = v6.ProductID_Mini1StarBox_15
local v89 = v_u_2:new()
local v90 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 15, v7:get_mini_1star_box_id()) }
local l_ProductID_Mini1StarBox_40_0 = v6.ProductID_Mini1StarBox_40
local v91 = v_u_2:new()
local v92 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 40, v7:get_mini_1star_box_id()) }
local l_ProductID_Mini1StarBox_80_0 = v6.ProductID_Mini1StarBox_80
local v93 = v_u_2:new()
local v94 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 80, v7:get_mini_1star_box_id()) }
local l_ProductID_Mini2StarBox_1_0 = v6.ProductID_Mini2StarBox_1
local v95 = v_u_2:new()
local v96 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 1, v7:get_mini_2star_box_id()) }
local l_ProductID_Mini2StarBox_5_0 = v6.ProductID_Mini2StarBox_5
local v97 = v_u_2:new()
local v98 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 5, v7:get_mini_2star_box_id()) }
local l_ProductID_Mini2StarBox_15_0 = v6.ProductID_Mini2StarBox_15
local v99 = v_u_2:new()
local v100 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 15, v7:get_mini_2star_box_id()) }
local l_ProductID_Mini2StarBox_35_0 = v6.ProductID_Mini2StarBox_35
local v101 = v_u_2:new()
local v102 = { v5.RewardInfo:new(v5.RewardType.CraftingMaterials, 35, v7:get_mini_2star_box_id()) }
local v_u_103 = v9:add_table(v10)
local v104 = {}
for v105, v106 in v6:get_copy_from_product_ids_map():key_itr() do
    v3:is_true(v_u_103:contains(v106))
    v_u_103:add(v105, v_u_103:get(v106))
end;
for _, v107 in pairs(v6:get_purchase_info_definitions_table()) do
    v3:is_true(v_u_103:contains(v107.ProductID))
    v3:is_true(v_u_103:get(v107.ProductID):count() > 0)
end;
v104.get_reward_info_list_for_purchase_id = function(_, p108) --[[ Name: get_reward_info_list_for_purchase_id ]] --[[ Line: 196 ]]
    --[[ Upvalues: (copy 1): v_u_103, (copy 2): v_u_4, (copy 3): v_u_2 ]]
    if v_u_103:contains(p108) == true then
        return v_u_103:get(p108);
    end;
    v_u_4:warnf("PurchaseInfoRewardDescription:get_reward_info_list_for_purchase_id(%s) no entry", (tostring(p108)))
    return v_u_2:new();
end;
return v104;
